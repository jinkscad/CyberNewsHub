import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Header from './components/Header';
import Filters from './components/Filters';
import ArticleList from './components/ArticleList';
import Stats from './components/Stats';
import LoadingSpinner from './components/LoadingSpinner';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function App() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [stats, setStats] = useState(null);
  const [sources, setSources] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState({
    category: '',
    source: '',
    search: '',
    days: ''
  });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [fastMode, setFastMode] = useState(false);

  useEffect(() => {
    loadSources();
    loadCategories();
    loadStats();
    loadArticles();
  }, [filters, page]);

  const loadArticles = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        per_page: 50,
        ...filters
      };
      // Remove empty filters
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null) {
          delete params[key];
        }
      });
      
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

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const handleFetchFeeds = async () => {
    setFetching(true);
    try {
      const startTime = Date.now();
      const response = await axios.post(`${API_BASE}/feeds/fetch`, {
        only_recent: fastMode,
        recent_days: 1, // 1 day = 24 hours
        max_workers: 10
      }, {
        timeout: fastMode ? 60000 : 120000 // 1 min for fast mode, 2 min for full
      });
      
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      
      const { new_articles, total_fetched, successful_feeds, failed_feeds, old_articles_deleted, retention_days } = response.data;
      
      let message = `Successfully fetched ${new_articles} new articles from ${total_fetched} total articles!\n\n`;
      message += `${successful_feeds} feeds succeeded\n`;
      if (failed_feeds > 0) {
        message += `${failed_feeds} feeds failed (this is normal - some feeds may be temporarily unavailable)\n`;
      }
      if (old_articles_deleted > 0) {
        message += `\nCleaned up ${old_articles_deleted} old articles (keeping last ${retention_days} days)\n`;
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
        onFetchFeeds={handleFetchFeeds} 
        fetching={fetching}
        fastMode={fastMode}
        onToggleFastMode={() => setFastMode(!fastMode)}
        onReCategorize={handleReCategorize}
      />
      <div className="container">
        <Stats stats={stats} />
        <Filters
          filters={filters}
          sources={sources}
          categories={categories}
          onFilterChange={handleFilterChange}
        />
        {loading ? (
          <LoadingSpinner />
        ) : (
          <>
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

