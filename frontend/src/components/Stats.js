import React from 'react';
import './Stats.css';

function Stats({ stats, hasActiveFilters }) {
  if (!stats) return null;

  return (
    <div className="stats-container">
      <div className="stat-card">
        <div className="stat-icon blue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.total_articles?.toLocaleString() || 0}</div>
          <div className="stat-label">
            {hasActiveFilters ? 'Matching Articles' : 'Total Articles'}
          </div>
        </div>
      </div>
      <div className="stat-card">
        <div className="stat-icon green">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
        </div>
        <div className="stat-content">
          <div className="stat-value">{stats.recent_articles_24h?.toLocaleString() || 0}</div>
          <div className="stat-label">
            {hasActiveFilters ? 'Matching (24h)' : 'Last 24 Hours'}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Stats;
