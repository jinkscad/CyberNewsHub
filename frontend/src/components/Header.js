import React from 'react';
import './Header.css';

function Header({ onFetchFeeds, fetching }) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-title">
          <h1>🛡️ CyberNewsHub</h1>
          <p className="subtitle">Global Cybersecurity News Aggregator</p>
        </div>
        <button
          className="fetch-btn"
          onClick={onFetchFeeds}
          disabled={fetching}
        >
          {fetching ? 'Fetching...' : '🔄 Fetch Latest News'}
        </button>
      </div>
    </header>
  );
}

export default Header;

