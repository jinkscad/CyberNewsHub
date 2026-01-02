import React, { useState, useEffect } from 'react';
import './FetchSettingsModal.css';

// Country flag emoji mapping (same as Filters.js)
const countryFlags = {
  'Argentina': '🇦🇷', 'Australia': '🇦🇺', 'Austria': '🇦🇹', 'Bangladesh': '🇧🇩',
  'Belgium': '🇧🇪', 'Bolivia': '🇧🇴', 'Brazil': '🇧🇷', 'Bulgaria': '🇧🇬',
  'Cambodia': '🇰🇭', 'Canada': '🇨🇦', 'Chile': '🇨🇱', 'China': '🇨🇳',
  'Colombia': '🇨🇴', 'Croatia': '🇭🇷', 'Cyprus': '🇨🇾', 'Czech Republic': '🇨🇿',
  'Denmark': '🇩🇰', 'Ecuador': '🇪🇨', 'Egypt': '🇪🇬', 'Estonia': '🇪🇪',
  'European Union': '🇪🇺', 'Finland': '🇫🇮', 'France': '🇫🇷', 'Germany': '🇩🇪',
  'Greece': '🇬🇷', 'Hong Kong': '🇭🇰', 'Hungary': '🇭🇺', 'India': '🇮🇳',
  'Indonesia': '🇮🇩', 'Ireland': '🇮🇪', 'Israel': '🇮🇱', 'Italy': '🇮🇹',
  'Japan': '🇯🇵', 'Kenya': '🇰🇪', 'Laos': '🇱🇦', 'Latvia': '🇱🇻',
  'Lithuania': '🇱🇹', 'Luxembourg': '🇱🇺', 'Malaysia': '🇲🇾', 'Malta': '🇲🇹',
  'Mexico': '🇲🇽', 'Morocco': '🇲🇦', 'Myanmar': '🇲🇲', 'Netherlands': '🇳🇱',
  'New Zealand': '🇳🇿', 'Nigeria': '🇳🇬', 'Norway': '🇳🇴', 'Pakistan': '🇵🇰',
  'Paraguay': '🇵🇾', 'Peru': '🇵🇪', 'Philippines': '🇵🇭', 'Poland': '🇵🇱',
  'Portugal': '🇵🇹', 'Romania': '🇷🇴', 'Russia': '🇷🇺', 'Saudi Arabia': '🇸🇦',
  'Singapore': '🇸🇬', 'Slovakia': '🇸🇰', 'Slovenia': '🇸🇮', 'South Africa': '🇿🇦',
  'South Korea': '🇰🇷', 'Spain': '🇪🇸', 'Sri Lanka': '🇱🇰', 'Sweden': '🇸🇪',
  'Switzerland': '🇨🇭', 'Taiwan': '🇹🇼', 'Thailand': '🇹🇭', 'Tunisia': '🇹🇳',
  'Turkey': '🇹🇷', 'Ukraine': '🇺🇦', 'United Arab Emirates': '🇦🇪',
  'United Kingdom': '🇬🇧', 'United States': '🇺🇸', 'Uruguay': '🇺🇾',
  'Venezuela': '🇻🇪', 'Vietnam': '🇻🇳', 'Algeria': '🇩🇿',
};

function FetchSettingsModal({ isOpen, onClose, onFetch, sourceCountries, isLoading }) {
  const [selectedCountries, setSelectedCountries] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  // Reset selection when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedCountries([]);
      setSearchQuery('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const getCountryFlag = (country) => countryFlags[country] || '🌍';

  // Sort countries by source count (descending), then alphabetically
  const sortedCountries = Object.entries(sourceCountries)
    .sort((a, b) => {
      if (b[1] !== a[1]) return b[1] - a[1]; // Sort by count descending
      return a[0].localeCompare(b[0]); // Then alphabetically
    });

  // Filter by search
  const filteredCountries = sortedCountries.filter(([country]) =>
    country.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleToggleCountry = (country) => {
    setSelectedCountries(prev =>
      prev.includes(country)
        ? prev.filter(c => c !== country)
        : [...prev, country]
    );
  };

  const handleSelectAll = () => {
    setSelectedCountries(Object.keys(sourceCountries));
  };

  const handleClearAll = () => {
    setSelectedCountries([]);
  };

  const handleFetch = () => {
    // If no countries selected, fetch all (pass null)
    const countries = selectedCountries.length > 0 ? selectedCountries : null;
    onFetch(countries);
  };

  const totalSources = Object.values(sourceCountries).reduce((a, b) => a + b, 0);
  const selectedSources = selectedCountries.reduce((sum, country) =>
    sum + (sourceCountries[country] || 0), 0
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Advanced Fetch Settings</h2>
          <button className="modal-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          <p className="modal-description">
            Select which countries to fetch news from. Only countries with configured RSS sources are shown.
          </p>

          <div className="country-search-container">
            <input
              type="text"
              className="country-search-input"
              placeholder="Search countries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
          </div>

          <div className="selection-controls">
            <button
              type="button"
              className="control-btn"
              onClick={handleSelectAll}
            >
              Select All ({Object.keys(sourceCountries).length})
            </button>
            <button
              type="button"
              className="control-btn"
              onClick={handleClearAll}
              disabled={selectedCountries.length === 0}
            >
              Clear All
            </button>
            <span className="selection-info">
              {selectedCountries.length > 0
                ? `${selectedCountries.length} countries (${selectedSources} sources)`
                : `All countries (${totalSources} sources)`
              }
            </span>
          </div>

          <div className="countries-grid">
            {filteredCountries.map(([country, sourceCount]) => (
              <label key={country} className="country-checkbox-item">
                <input
                  type="checkbox"
                  checked={selectedCountries.includes(country)}
                  onChange={() => handleToggleCountry(country)}
                />
                <span className="country-label">
                  <span className="country-flag">{getCountryFlag(country)}</span>
                  <span className="country-name">{country}</span>
                  <span className="source-count">({sourceCount})</span>
                </span>
              </label>
            ))}
          </div>

          {filteredCountries.length === 0 && (
            <div className="no-results">No countries found matching "{searchQuery}"</div>
          )}
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn-cancel"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn-fetch"
            onClick={handleFetch}
            disabled={isLoading}
          >
            {isLoading
              ? 'Fetching...'
              : selectedCountries.length > 0
                ? `Fetch from ${selectedCountries.length} Countries`
                : 'Fetch All Countries'
            }
          </button>
        </div>
      </div>
    </div>
  );
}

export default FetchSettingsModal;
