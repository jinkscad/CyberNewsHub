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
        <div className="stat-value">{stats.recent_articles_24h?.toLocaleString() || 0}</div>
        <div className="stat-label">Last 24 hrs</div>
      </div>
    </div>
  );
}

export default Stats;

