import React from 'react';
import './Header.css';

function Header({ onFetchFeeds, fetching, fastMode, onToggleFastMode, onReCategorize }) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-title">
          <h1>CyberNewsHub</h1>
          <p className="subtitle">Global Cybersecurity News Aggregator</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#00d970', fontSize: '0.85rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={fastMode}
              onChange={onToggleFastMode}
              style={{ cursor: 'pointer' }}
            />
            <span>Fast mode (last 24 hrs only)</span>
          </label>
          <button
            className="fetch-btn"
            onClick={onReCategorize}
            disabled={fetching}
            style={{ fontSize: '12px', padding: '10px 16px' }}
            title="Re-categorize all articles"
          >
            Re-categorize
          </button>
          <button
            className="fetch-btn"
            onClick={onFetchFeeds}
            disabled={fetching}
          >
            {fetching ? 'Fetching...' : 'Fetch Latest News'}
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;

