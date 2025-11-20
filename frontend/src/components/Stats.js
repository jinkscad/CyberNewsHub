import React from 'react';
import './Stats.css';

function Stats({ stats }) {
  if (!stats) return null;

  return (
    <div className="stats-container">
      <div className="stat-card">
        <div className="stat-value">{stats.total_articles?.toLocaleString() || 0}</div>
        <div className="stat-label">Total Articles</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.recent_articles_7d?.toLocaleString() || 0}</div>
        <div className="stat-label">Last 7 Days</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">
          {Object.keys(stats.by_category || {}).length}
        </div>
        <div className="stat-label">Categories</div>
      </div>
    </div>
  );
}

export default Stats;

