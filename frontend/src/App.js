import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Header from './components/Header';
import Filters from './components/Filters';
import ArticleList from './components/ArticleList';
import Stats from './components/Stats';
import LoadingSpinner from './components/LoadingSpinner';
import FetchSettingsModal from './components/FetchSettingsModal';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function App() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [stats, setStats] = useState(null);
  const [sources, setSources] = useState([]);
  const [categories, setCategories] = useState([]);
  const [countries, setCountries] = useState([]);
  const [filters, setFilters] = useState({
    category: '',
    source: '',
    search: '',
    days: '',
    countries: [],
    sort_by: 'newest'
  });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [fastMode, setFastMode] = useState(false);
  const [fetchSettingsOpen, setFetchSettingsOpen] = useState(false);
  const [sourceCountries, setSourceCountries] = useState({});
  
  // Check if any filters are active
  const hasActiveFilters = filters.category || filters.source || filters.search || filters.days || (filters.countries && filters.countries.length > 0);

  useEffect(() => {
    loadSources();
    loadCategories();
    loadCountries();
    loadStats();
    loadArticles();
    loadSourceCountries();
  }, [filters, page]);

  const loadSourceCountries = async () => {
    try {
      const response = await axios.get(`${API_BASE}/feeds/sources-by-country`);
      setSourceCountries(response.data.countries || {});
    } catch (error) {
      console.error('Error loading source countries:', error);
    }
  };

  const loadArticles = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        per_page: 50,
        ...filters
      };
      // Handle countries array - convert to comma-separated string
      if (params.countries && Array.isArray(params.countries) && params.countries.length > 0) {
        params.countries = params.countries.join(',');
      } else {
        delete params.countries;
      }
      // Remove empty filters (but always keep sort_by)
      Object.keys(params).forEach(key => {
        if (key === 'sort_by') {
          // Always include sort_by, even if it's the default
          return;
        }
        if (params[key] === '' || params[key] === null || (Array.isArray(params[key]) && params[key].length === 0)) {
          delete params[key];
        }
      });
      // Ensure sort_by is always set (default to 'newest')
      if (!params.sort_by) {
        params.sort_by = 'newest';
      }
      
      const response = await axios.get(`${API_BASE}/articles`, { params });
      setArticles(response.data.articles);
      setTotalPages(response.data.pages);
    } catch (error) {
      console.error('Error loading articles:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSources = async () => {
    try {
      const response = await axios.get(`${API_BASE}/articles/sources`);
      setSources(response.data.sources);
    } catch (error) {
      console.error('Error loading sources:', error);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await axios.get(`${API_BASE}/articles/categories`);
      setCategories(response.data.categories);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const loadCountries = async () => {
    try {
      const response = await axios.get(`${API_BASE}/articles/countries`);
      setCountries(response.data.countries);
    } catch (error) {
      console.error('Error loading countries:', error);
    }
  };

  const loadStats = async () => {
    try {
      // Pass current filters to stats endpoint
      const params = {
        ...filters
      };
      // Handle countries array - convert to comma-separated string
      if (params.countries && Array.isArray(params.countries) && params.countries.length > 0) {
        params.countries = params.countries.join(',');
      } else {
        delete params.countries;
      }
      // Remove empty filters
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null || (Array.isArray(params[key]) && params[key].length === 0)) {
          delete params[key];
        }
      });
      
      const response = await axios.get(`${API_BASE}/stats`, { params });
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleFetchFeeds = async (selectedCountries = null) => {
    setFetching(true);
    setFetchSettingsOpen(false); // Close modal when fetching starts
    try {
      const startTime = Date.now();
      const requestBody = {
        only_recent: fastMode,
        recent_days: 1, // 1 day = 24 hours
        max_workers: 10
      };
      // Add countries filter if specified
      if (selectedCountries && selectedCountries.length > 0) {
        requestBody.countries = selectedCountries;
      }
      const response = await axios.post(`${API_BASE}/feeds/fetch`, requestBody, {
        timeout: fastMode ? 60000 : 180000 // 1 min for fast mode, 3 min for full
      });
      
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      
      const { new_articles, total_fetched, successful_feeds, cached_feeds, failed_feeds, failed_feed_details, old_articles_deleted, retention_days } = response.data;

      let message = `Successfully fetched ${new_articles} new articles from ${total_fetched} total articles!\n\n`;
      message += `${successful_feeds} feeds with new articles\n`;
      if (cached_feeds > 0) {
        message += `${cached_feeds} feeds cached (no changes)\n`;
      }
      if (failed_feeds > 0) {
        message += `${failed_feeds} feeds failed\n\n`;
        
        // Show error details if available
        if (failed_feed_details && failed_feed_details.length > 0) {
          message += `Error Details (first ${Math.min(10, failed_feed_details.length)}):\n`;
          message += '─'.repeat(50) + '\n';
          failed_feed_details.slice(0, 10).forEach((detail, idx) => {
            message += `${idx + 1}. ${detail.name}\n`;
            message += `   Error: ${detail.error}\n`;
            if (detail.url) {
              message += `   URL: ${detail.url.substring(0, 60)}${detail.url.length > 60 ? '...' : ''}\n`;
            }
            message += '\n';
          });
          if (failed_feed_details.length > 10) {
            message += `... and ${failed_feed_details.length - 10} more (check backend.log for full details)\n\n`;
          }
          message += 'Check backend.log for complete error details.\n\n';
        }
      }
      if (old_articles_deleted > 0) {
        message += `Cleaned up ${old_articles_deleted} old articles (keeping last ${retention_days} days)\n`;
      }
      message += `\nCompleted in ${elapsed} seconds`;
      
      alert(message);
      // Reload everything to show updated counts
      loadArticles();
      loadStats();
      loadCategories(); // Also reload categories in case new ones appeared
    } catch (error) {
      console.error('Error fetching feeds:', error);
      let errorMessage = 'Error fetching feeds. ';
      if (error.code === 'ECONNABORTED') {
        errorMessage += 'Request timed out. This may take a while - please try again.';
      } else if (error.response) {
        errorMessage += error.response.data?.message || 'Please check the backend logs.';
      } else {
        errorMessage += 'Please make sure the backend is running.';
      }
      alert(errorMessage);
    } finally {
      setFetching(false);
    }
  };

  const handleReCategorize = async () => {
    if (!window.confirm('Re-categorize all articles? This will update categories and country/region tags based on article content.')) {
      return;
    }
    
    setFetching(true);
    try {
      const response = await axios.post(`${API_BASE}/articles/re-categorize`);
      let message = `Successfully updated articles!\n\n`;
      if (response.data.categories_updated > 0) {
        message += `${response.data.categories_updated} categories updated\n`;
      }
      if (response.data.regions_updated > 0) {
        message += `${response.data.regions_updated} country/region tags updated\n`;
      }
      message += `\nCategories: News, Event, Research, Alert`;
      alert(message);
      loadArticles();
      loadCategories();
    } catch (error) {
      console.error('Error re-categorizing:', error);
      alert('Error re-categorizing articles. Please try again.');
    } finally {
      setFetching(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1); // Reset to first page when filters change
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="App">
      <Header
        onFetchFeeds={() => handleFetchFeeds(null)}
        fetching={fetching}
        fastMode={fastMode}
        onToggleFastMode={() => setFastMode(!fastMode)}
        onReCategorize={handleReCategorize}
        onOpenFetchSettings={() => setFetchSettingsOpen(true)}
      />
      <FetchSettingsModal
        isOpen={fetchSettingsOpen}
        onClose={() => setFetchSettingsOpen(false)}
        onFetch={handleFetchFeeds}
        sourceCountries={sourceCountries}
        isLoading={fetching}
      />
      <div className="container">
        <Stats stats={stats} hasActiveFilters={hasActiveFilters} />
        <Filters
          filters={filters}
          sources={sources}
          categories={categories}
          countries={countries}
          onFilterChange={handleFilterChange}
        />
        {loading ? (
          <LoadingSpinner />
        ) : (
          <>
            <div className="article-toolbar">
              <div className="sort-control">
                <label htmlFor="sort_by">Sort By:</label>
                <select
                  id="sort_by"
                  value={filters.sort_by || 'newest'}
                  onChange={(e) => handleFilterChange('sort_by', e.target.value)}
                  className="sort-select"
                >
                  <option value="newest">Newest First</option>
                  <option value="oldest">Oldest First</option>
                </select>
              </div>
            </div>
            <ArticleList articles={articles} />
            {totalPages > 1 && (
              <div className="pagination">
                <button
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page === 1}
                  className="page-btn"
                >
                  Previous
                </button>
                <span className="page-info">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page === totalPages}
                  className="page-btn"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;

