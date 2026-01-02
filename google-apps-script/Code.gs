/**
 * CyberNewsHub - Google Apps Script API
 *
 * This script turns a Google Spreadsheet into a REST API backend.
 *
 * SETUP:
 * 1. Create a new Google Spreadsheet
 * 2. Create two sheets named "Articles" and "FeedCache"
 * 3. Go to Extensions > Apps Script
 * 4. Paste this code and save
 * 5. Deploy > New deployment > Web app
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 6. Copy the Web App URL and use it in your Flask backend
 */

// Configuration
const ARTICLES_SHEET_NAME = 'Articles';
const FEED_CACHE_SHEET_NAME = 'FeedCache';
const MAX_ARTICLES = 5000;  // Maximum number of articles to store (free tier friendly)

// Article columns (order matters - matches spreadsheet columns)
const ARTICLE_COLUMNS = [
  'id', 'title', 'link', 'description', 'source',
  'publisher_type', 'content_type', 'country_region',
  'published_date', 'fetched_date'
];

// FeedCache columns
const FEED_CACHE_COLUMNS = [
  'id', 'feed_url', 'etag', 'last_modified', 'last_fetched', 'content_hash'
];

/**
 * Initialize sheets with headers if they don't exist
 */
function initializeSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // Initialize Articles sheet
  let articlesSheet = ss.getSheetByName(ARTICLES_SHEET_NAME);
  if (!articlesSheet) {
    articlesSheet = ss.insertSheet(ARTICLES_SHEET_NAME);
    articlesSheet.getRange(1, 1, 1, ARTICLE_COLUMNS.length).setValues([ARTICLE_COLUMNS]);
    articlesSheet.getRange(1, 1, 1, ARTICLE_COLUMNS.length).setFontWeight('bold');
    articlesSheet.setFrozenRows(1);
  }

  // Initialize FeedCache sheet
  let feedCacheSheet = ss.getSheetByName(FEED_CACHE_SHEET_NAME);
  if (!feedCacheSheet) {
    feedCacheSheet = ss.insertSheet(FEED_CACHE_SHEET_NAME);
    feedCacheSheet.getRange(1, 1, 1, FEED_CACHE_COLUMNS.length).setValues([FEED_CACHE_COLUMNS]);
    feedCacheSheet.getRange(1, 1, 1, FEED_CACHE_COLUMNS.length).setFontWeight('bold');
    feedCacheSheet.setFrozenRows(1);
  }

  return { articlesSheet, feedCacheSheet };
}

/**
 * GET request handler
 */
function doGet(e) {
  try {
    const action = e.parameter.action || 'articles';
    let result;

    switch (action) {
      case 'articles':
        result = getArticles(e.parameter);
        break;
      case 'sources':
        result = getDistinctValues('source');
        break;
      case 'categories':
        result = getDistinctValues('content_type');
        break;
      case 'publisher-types':
        result = getDistinctValues('publisher_type');
        break;
      case 'countries':
        result = getDistinctCountries();
        break;
      case 'stats':
        result = getStats(e.parameter);
        break;
      case 'feed-cache':
        result = getFeedCache(e.parameter.feed_url);
        break;
      case 'health':
        result = { status: 'ok', timestamp: new Date().toISOString() };
        break;
      default:
        result = { error: 'Unknown action: ' + action };
    }

    return createJsonResponse(result);
  } catch (error) {
    return createJsonResponse({ error: error.message, stack: error.stack });
  }
}

/**
 * POST request handler
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const action = data.action || 'add-articles';
    let result;

    switch (action) {
      case 'add-articles':
        result = addArticles(data.articles || []);
        break;
      case 'update-feed-cache':
        result = updateFeedCache(data.cache);
        break;
      case 'cleanup':
        result = cleanupOldArticles(data.days || 90);
        break;
      case 'delete-by-source':
        result = deleteBySource(data.source);
        break;
      case 'delete-article':
        result = deleteArticle(data.link);
        break;
      default:
        result = { error: 'Unknown action: ' + action };
    }

    return createJsonResponse(result);
  } catch (error) {
    return createJsonResponse({ error: error.message, stack: error.stack });
  }
}

/**
 * Create JSON response with CORS headers
 */
function createJsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Get articles with filtering and pagination
 */
function getArticles(params) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1) {
    return { articles: [], total: 0, page: 1, per_page: 50, pages: 0 };
  }

  // Get all data (skip header row)
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, ARTICLE_COLUMNS.length).getValues();

  // Convert to objects
  let articles = data.map(row => rowToArticle(row)).filter(a => a.link); // Filter empty rows

  // Apply filters
  if (params.category) {
    articles = articles.filter(a => a.content_type === params.category);
  }

  if (params.publisher_type) {
    articles = articles.filter(a => a.publisher_type === params.publisher_type);
  }

  if (params.source) {
    articles = articles.filter(a => a.source === params.source);
  }

  if (params.search) {
    const searchLower = params.search.toLowerCase();
    articles = articles.filter(a =>
      (a.title && a.title.toLowerCase().includes(searchLower)) ||
      (a.description && a.description.toLowerCase().includes(searchLower))
    );
  }

  if (params.countries) {
    const countryList = params.countries.split(',').map(c => c.trim().toLowerCase());
    articles = articles.filter(a => {
      if (!a.country_region) return false;
      const articleCountries = a.country_region.toLowerCase();
      return countryList.some(c => articleCountries.includes(c));
    });
  }

  if (params.days) {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - parseInt(params.days));
    articles = articles.filter(a => new Date(a.published_date) >= cutoffDate);
  }

  // Filter out future articles (more than 24 hours in the future)
  const futureLimit = new Date();
  futureLimit.setHours(futureLimit.getHours() + 24);
  articles = articles.filter(a => new Date(a.published_date) <= futureLimit);

  const total = articles.length;

  // Sort
  const sortOrder = params.sort || 'newest';
  if (sortOrder === 'newest') {
    articles.sort((a, b) => new Date(b.published_date) - new Date(a.published_date));
  } else if (sortOrder === 'oldest') {
    articles.sort((a, b) => new Date(a.published_date) - new Date(b.published_date));
  }

  // Pagination
  const page = parseInt(params.page) || 1;
  const perPage = parseInt(params.per_page) || 50;
  const startIndex = (page - 1) * perPage;
  const paginatedArticles = articles.slice(startIndex, startIndex + perPage);

  return {
    articles: paginatedArticles,
    total: total,
    page: page,
    per_page: perPage,
    pages: Math.ceil(total / perPage)
  };
}

/**
 * Convert spreadsheet row to article object
 */
function rowToArticle(row) {
  const article = {};
  ARTICLE_COLUMNS.forEach((col, index) => {
    let value = row[index];
    // Format dates as ISO strings
    if ((col === 'published_date' || col === 'fetched_date') && value instanceof Date) {
      value = value.toISOString();
    }
    article[col] = value;
  });
  return article;
}

/**
 * Add multiple articles (with duplicate checking)
 */
function addArticles(articles) {
  if (!articles || articles.length === 0) {
    return { added: 0, duplicates: 0 };
  }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  // Initialize if needed
  if (!sheet) {
    initializeSheets();
    sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);
  }

  // Get existing links for duplicate detection
  const existingLinks = new Set();
  if (sheet.getLastRow() > 1) {
    const linkColumn = ARTICLE_COLUMNS.indexOf('link') + 1;
    const links = sheet.getRange(2, linkColumn, sheet.getLastRow() - 1, 1).getValues();
    links.forEach(row => existingLinks.add(row[0]));
  }

  // Filter out duplicates and prepare rows
  const newRows = [];
  let duplicates = 0;

  // Get next ID
  let nextId = 1;
  if (sheet.getLastRow() > 1) {
    const ids = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
    const maxId = Math.max(...ids.map(row => parseInt(row[0]) || 0));
    nextId = maxId + 1;
  }

  articles.forEach(article => {
    if (existingLinks.has(article.link)) {
      duplicates++;
      return;
    }

    existingLinks.add(article.link); // Prevent duplicates within batch

    const row = ARTICLE_COLUMNS.map(col => {
      if (col === 'id') return nextId++;
      if (col === 'fetched_date' && !article[col]) {
        return new Date().toISOString();
      }
      return article[col] || '';
    });

    newRows.push(row);
  });

  // Batch insert
  if (newRows.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, newRows.length, ARTICLE_COLUMNS.length)
      .setValues(newRows);
  }

  // Enforce capacity limit - delete oldest articles if over MAX_ARTICLES
  let deletedForCapacity = 0;
  const totalRows = sheet.getLastRow() - 1; // Exclude header
  if (totalRows > MAX_ARTICLES) {
    const rowsToDelete = totalRows - MAX_ARTICLES;
    // Delete from row 2 (after header), oldest articles are at the top after sorting
    // First, sort by published_date ascending so oldest are at top
    const dateColumnIndex = ARTICLE_COLUMNS.indexOf('published_date') + 1;
    const dataRange = sheet.getRange(2, 1, totalRows, ARTICLE_COLUMNS.length);
    dataRange.sort({ column: dateColumnIndex, ascending: true });
    // Delete the oldest rows (from top)
    sheet.deleteRows(2, rowsToDelete);
    deletedForCapacity = rowsToDelete;
  }

  return { added: newRows.length, duplicates: duplicates, deleted_for_capacity: deletedForCapacity, max_articles: MAX_ARTICLES };
}

/**
 * Get distinct values from a column
 */
function getDistinctValues(columnName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1) {
    return { values: [] };
  }

  const columnIndex = ARTICLE_COLUMNS.indexOf(columnName) + 1;
  const values = sheet.getRange(2, columnIndex, sheet.getLastRow() - 1, 1).getValues();

  const uniqueValues = [...new Set(values.map(row => row[0]).filter(v => v))];
  uniqueValues.sort();

  return { values: uniqueValues };
}

/**
 * Get distinct countries (handles comma-separated values)
 */
function getDistinctCountries() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1) {
    return { values: [] };
  }

  const columnIndex = ARTICLE_COLUMNS.indexOf('country_region') + 1;
  const values = sheet.getRange(2, columnIndex, sheet.getLastRow() - 1, 1).getValues();

  const countries = new Set();
  values.forEach(row => {
    if (row[0]) {
      // Split comma-separated countries
      row[0].toString().split(',').forEach(c => {
        const trimmed = c.trim();
        if (trimmed) countries.add(trimmed);
      });
    }
  });

  const sortedCountries = [...countries].sort();
  return { values: sortedCountries };
}

/**
 * Get statistics
 */
function getStats(params) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1) {
    return {
      total_articles: 0,
      recent_articles_24h: 0,
      by_publisher_type: {},
      by_content_type: {},
      oldest_article_date: null
    };
  }

  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, ARTICLE_COLUMNS.length).getValues();
  let articles = data.map(row => rowToArticle(row)).filter(a => a.link);

  // Apply days filter if provided
  if (params.days) {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - parseInt(params.days));
    articles = articles.filter(a => new Date(a.published_date) >= cutoffDate);
  }

  // Calculate 24h count
  const yesterday = new Date();
  yesterday.setHours(yesterday.getHours() - 24);
  const recent24h = articles.filter(a => new Date(a.published_date) >= yesterday).length;

  // Group by publisher_type
  const byPublisherType = {};
  articles.forEach(a => {
    const type = a.publisher_type || 'Unknown';
    byPublisherType[type] = (byPublisherType[type] || 0) + 1;
  });

  // Group by content_type
  const byContentType = {};
  articles.forEach(a => {
    const type = a.content_type || 'Unknown';
    byContentType[type] = (byContentType[type] || 0) + 1;
  });

  // Find oldest article
  let oldestDate = null;
  if (articles.length > 0) {
    const dates = articles.map(a => new Date(a.published_date)).filter(d => !isNaN(d));
    if (dates.length > 0) {
      oldestDate = new Date(Math.min(...dates)).toISOString();
    }
  }

  return {
    total_articles: articles.length,
    recent_articles_24h: recent24h,
    by_publisher_type: byPublisherType,
    by_content_type: byContentType,
    oldest_article_date: oldestDate
  };
}

/**
 * Clean up articles older than specified days
 */
function cleanupOldArticles(days) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1) {
    return { deleted: 0 };
  }

  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - days);

  const dateColumnIndex = ARTICLE_COLUMNS.indexOf('published_date') + 1;
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, ARTICLE_COLUMNS.length).getValues();

  // Find rows to delete (from bottom to top to preserve indices)
  const rowsToDelete = [];
  data.forEach((row, index) => {
    const publishedDate = new Date(row[dateColumnIndex - 1]);
    if (publishedDate < cutoffDate) {
      rowsToDelete.push(index + 2); // +2 for header and 0-indexing
    }
  });

  // Delete from bottom to top
  rowsToDelete.reverse().forEach(rowNum => {
    sheet.deleteRow(rowNum);
  });

  return { deleted: rowsToDelete.length };
}

/**
 * Delete articles by source
 */
function deleteBySource(source) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1 || !source) {
    return { deleted: 0 };
  }

  const sourceColumnIndex = ARTICLE_COLUMNS.indexOf('source') + 1;
  const data = sheet.getRange(2, sourceColumnIndex, sheet.getLastRow() - 1, 1).getValues();

  const rowsToDelete = [];
  data.forEach((row, index) => {
    if (row[0] === source) {
      rowsToDelete.push(index + 2);
    }
  });

  rowsToDelete.reverse().forEach(rowNum => {
    sheet.deleteRow(rowNum);
  });

  return { deleted: rowsToDelete.length };
}

/**
 * Delete single article by link
 */
function deleteArticle(link) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1 || !link) {
    return { deleted: false };
  }

  const linkColumnIndex = ARTICLE_COLUMNS.indexOf('link') + 1;
  const data = sheet.getRange(2, linkColumnIndex, sheet.getLastRow() - 1, 1).getValues();

  for (let i = 0; i < data.length; i++) {
    if (data[i][0] === link) {
      sheet.deleteRow(i + 2);
      return { deleted: true };
    }
  }

  return { deleted: false };
}

/**
 * Get feed cache entry
 */
function getFeedCache(feedUrl) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(FEED_CACHE_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1 || !feedUrl) {
    return { cache: null };
  }

  const urlColumnIndex = FEED_CACHE_COLUMNS.indexOf('feed_url') + 1;
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, FEED_CACHE_COLUMNS.length).getValues();

  for (const row of data) {
    if (row[urlColumnIndex - 1] === feedUrl) {
      const cache = {};
      FEED_CACHE_COLUMNS.forEach((col, index) => {
        cache[col] = row[index];
      });
      return { cache: cache };
    }
  }

  return { cache: null };
}

/**
 * Update or insert feed cache entry
 */
function updateFeedCache(cacheData) {
  if (!cacheData || !cacheData.feed_url) {
    return { success: false, error: 'Missing feed_url' };
  }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(FEED_CACHE_SHEET_NAME);

  // Initialize if needed
  if (!sheet) {
    initializeSheets();
    sheet = ss.getSheetByName(FEED_CACHE_SHEET_NAME);
  }

  const urlColumnIndex = FEED_CACHE_COLUMNS.indexOf('feed_url') + 1;

  // Check if entry exists
  let existingRow = -1;
  if (sheet.getLastRow() > 1) {
    const data = sheet.getRange(2, urlColumnIndex, sheet.getLastRow() - 1, 1).getValues();
    for (let i = 0; i < data.length; i++) {
      if (data[i][0] === cacheData.feed_url) {
        existingRow = i + 2;
        break;
      }
    }
  }

  // Prepare row data
  let nextId = 1;
  if (existingRow === -1 && sheet.getLastRow() > 1) {
    const ids = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
    const maxId = Math.max(...ids.map(row => parseInt(row[0]) || 0));
    nextId = maxId + 1;
  }

  const row = FEED_CACHE_COLUMNS.map((col, index) => {
    if (col === 'id') {
      if (existingRow > 0) {
        return sheet.getRange(existingRow, 1).getValue();
      }
      return nextId;
    }
    if (col === 'last_fetched' && !cacheData[col]) {
      return new Date().toISOString();
    }
    return cacheData[col] || '';
  });

  if (existingRow > 0) {
    // Update existing
    sheet.getRange(existingRow, 1, 1, FEED_CACHE_COLUMNS.length).setValues([row]);
  } else {
    // Insert new
    sheet.getRange(sheet.getLastRow() + 1, 1, 1, FEED_CACHE_COLUMNS.length).setValues([row]);
  }

  return { success: true };
}

/**
 * Check if article exists by link
 */
function articleExists(link) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1) {
    return { exists: false };
  }

  const linkColumnIndex = ARTICLE_COLUMNS.indexOf('link') + 1;
  const data = sheet.getRange(2, linkColumnIndex, sheet.getLastRow() - 1, 1).getValues();

  for (const row of data) {
    if (row[0] === link) {
      return { exists: true };
    }
  }

  return { exists: false };
}

/**
 * Get all existing article links (for batch duplicate checking)
 */
function getExistingLinks() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(ARTICLES_SHEET_NAME);

  if (!sheet || sheet.getLastRow() <= 1) {
    return { links: [] };
  }

  const linkColumnIndex = ARTICLE_COLUMNS.indexOf('link') + 1;
  const data = sheet.getRange(2, linkColumnIndex, sheet.getLastRow() - 1, 1).getValues();

  return { links: data.map(row => row[0]).filter(l => l) };
}
