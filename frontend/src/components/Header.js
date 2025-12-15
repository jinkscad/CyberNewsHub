import React, { useState } from 'react';
import './Header.css';

function Header({ onFetchFeeds, fetching, fastMode, onToggleFastMode, onReCategorize }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="header">
      <div className="header-inner">
        <div className="logo">
          <div className="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L4 6V12C4 16.42 7.4 20.74 12 22C16.6 20.74 20 16.42 20 12V6L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M9 12L11 14L15 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="logo-text">
            <span className="logo-cyber">CYBER</span>
            <span className="logo-hub">NEWS</span>
          </div>
        </div>

        <nav className={`nav ${menuOpen ? 'nav-open' : ''}`}>
          <span className="nav-link active">Dashboard</span>
          <span className="nav-link">News</span>
          <span className="nav-link">Threats</span>
          <span className="nav-link">Analysis</span>
        </nav>

        <div className="header-actions">
          <div className="fast-mode-toggle">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={fastMode}
                onChange={onToggleFastMode}
              />
              <span className="toggle-slider"></span>
            </label>
            <span className="toggle-label">Fast Mode</span>
          </div>

          <button
            className="btn btn-secondary"
            onClick={onReCategorize}
            disabled={fetching}
          >
            Re-categorize
          </button>

          <button
            className="btn btn-primary"
            onClick={onFetchFeeds}
            disabled={fetching}
          >
            {fetching ? (
              <>
                <span className="btn-spinner"></span>
                Fetching...
              </>
            ) : (
              'Fetch News'
            )}
          </button>

          <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)}>
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
