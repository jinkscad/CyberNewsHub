import React from 'react';
import './Filters.css';

function Filters({ filters, sources, categories, onFilterChange }) {
  return (
    <div className="filters-container">
      <div className="filter-group">
        <label htmlFor="search">🔍 Search</label>
        <input
          id="search"
          type="text"
          placeholder="Search articles..."
          value={filters.search}
          onChange={(e) => onFilterChange('search', e.target.value)}
          className="filter-input"
        />
      </div>
      
      <div className="filter-group">
        <label htmlFor="category">📁 Category</label>
        <select
          id="category"
          value={filters.category}
          onChange={(e) => onFilterChange('category', e.target.value)}
          className="filter-select"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label htmlFor="source">📰 Source</label>
        <select
          id="source"
          value={filters.source}
          onChange={(e) => onFilterChange('source', e.target.value)}
          className="filter-select"
        >
          <option value="">All Sources</option>
          {sources.map(source => (
            <option key={source} value={source}>{source}</option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label htmlFor="days">📅 Time Range</label>
        <select
          id="days"
          value={filters.days}
          onChange={(e) => onFilterChange('days', e.target.value)}
          className="filter-select"
        >
          <option value="">All Time</option>
          <option value="1">Last 24 Hours</option>
          <option value="7">Last 7 Days</option>
          <option value="30">Last 30 Days</option>
          <option value="90">Last 90 Days</option>
        </select>
      </div>
      
      {(filters.category || filters.source || filters.search || filters.days) && (
        <button
          className="clear-filters-btn"
          onClick={() => {
            onFilterChange('category', '');
            onFilterChange('source', '');
            onFilterChange('search', '');
            onFilterChange('days', '');
          }}
        >
          Clear Filters
        </button>
      )}
    </div>
  );
}

export default Filters;

