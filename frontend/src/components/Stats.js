import React from 'react';
import './Stats.css';

function Stats({ stats, hasActiveFilters }) {
  if (!stats) return null;

  return (
    <div className="stats-container">
      <div className="stat-card">
        <div className="stat-value">{stats.total_articles?.toLocaleString() || 0}</div>
        <div className="stat-label">
          {hasActiveFilters ? 'Matching Articles' : 'Total Articles'}
        </div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.recent_articles_24h?.toLocaleString() || 0}</div>
        <div className="stat-label">
          {hasActiveFilters ? 'Matching (Last 24 hrs)' : 'Last 24 hrs'}
        </div>
      </div>
    </div>
  );
}

export default Stats;

