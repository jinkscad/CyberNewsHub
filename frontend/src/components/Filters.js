import React, { useState, useEffect, useRef } from 'react';
import './Filters.css';

// Country flag emoji mapping
const countryFlags = {
  'Argentina': '🇦🇷',
  'Australia': '🇦🇺',
  'Austria': '🇦🇹',
  'Bangladesh': '🇧🇩',
  'Belgium': '🇧🇪',
  'Bolivia': '🇧🇴',
  'Brazil': '🇧🇷',
  'Bulgaria': '🇧🇬',
  'Cambodia': '🇰🇭',
  'Canada': '🇨🇦',
  'Chile': '🇨🇱',
  'China': '🇨🇳',
  'Colombia': '🇨🇴',
  'Croatia': '🇭🇷',
  'Cyprus': '🇨🇾',
  'Czech Republic': '🇨🇿',
  'Denmark': '🇩🇰',
  'Ecuador': '🇪🇨',
  'Egypt': '🇪🇬',
  'Estonia': '🇪🇪',
  'European Union': '🇪🇺',
  'Finland': '🇫🇮',
  'France': '🇫🇷',
  'Germany': '🇩🇪',
  'Greece': '🇬🇷',
  'Hungary': '🇭🇺',
  'India': '🇮🇳',
  'Indonesia': '🇮🇩',
  'Ireland': '🇮🇪',
  'Israel': '🇮🇱',
  'Italy': '🇮🇹',
  'Japan': '🇯🇵',
  'Kenya': '🇰🇪',
  'Laos': '🇱🇦',
  'Latvia': '🇱🇻',
  'Lithuania': '🇱🇹',
  'Luxembourg': '🇱🇺',
  'Malaysia': '🇲🇾',
  'Malta': '🇲🇹',
  'Mexico': '🇲🇽',
  'Morocco': '🇲🇦',
  'Myanmar': '🇲🇲',
  'Netherlands': '🇳🇱',
  'New Zealand': '🇳🇿',
  'Nigeria': '🇳🇬',
  'Norway': '🇳🇴',
  'Pakistan': '🇵🇰',
  'Paraguay': '🇵🇾',
  'Peru': '🇵🇪',
  'Philippines': '🇵🇭',
  'Poland': '🇵🇱',
  'Portugal': '🇵🇹',
  'Romania': '🇷🇴',
  'Russia': '🇷🇺',
  'Saudi Arabia': '🇸🇦',
  'Singapore': '🇸🇬',
  'Slovakia': '🇸🇰',
  'Slovenia': '🇸🇮',
  'South Africa': '🇿🇦',
  'South Korea': '🇰🇷',
  'Spain': '🇪🇸',
  'Sri Lanka': '🇱🇰',
  'Sweden': '🇸🇪',
  'Switzerland': '🇨🇭',
  'Taiwan': '🇹🇼',
  'Thailand': '🇹🇭',
  'Tunisia': '🇹🇳',
  'Turkey': '🇹🇷',
  'United Arab Emirates': '🇦🇪',
  'United Kingdom': '🇬🇧',
  'United States': '🇺🇸',
  'Uruguay': '🇺🇾',
  'Venezuela': '🇻🇪',
  'Vietnam': '🇻🇳',
  'Algeria': '🇩🇿',
};

function Filters({ filters, sources, categories, countries, onFilterChange }) {
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');
  const countryDropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (countryDropdownRef.current && !countryDropdownRef.current.contains(event.target)) {
        setShowCountryDropdown(false);
      }
    };

    if (showCountryDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showCountryDropdown]);

  const handleCountryToggle = (country) => {
    const currentCountries = filters.countries || [];
    const newCountries = currentCountries.includes(country)
      ? currentCountries.filter(c => c !== country)
      : [...currentCountries, country];
    onFilterChange('countries', newCountries);
  };

  const handleClearCountries = () => {
    onFilterChange('countries', []);
  };

  const selectedCountriesCount = (filters.countries || []).length;

  // Filter countries based on search
  const filteredCountries = countries.filter(country => 
    country.toLowerCase().includes(countrySearch.toLowerCase())
  );

  const getCountryFlag = (country) => {
    return countryFlags[country] || '🌍';
  };

  return (
    <div className="filters-container">
      <div className="filter-group">
        <label htmlFor="search">Search</label>
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
        <label htmlFor="category">Category</label>
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
        <label htmlFor="source">Source</label>
        <select
          id="source"
          value={filters.source}
          onChange={(e) => onFilterChange('source', e.target.value)}
          className="filter-select"
        >
          <option value="">All Sources</option>
          {sources.map(source => {
            const sourceName = typeof source === 'string' ? source : source.name;
            const sourceCountry = typeof source === 'object' && source.country ? source.country : null;
            const displayName = sourceCountry ? `${sourceName} (${sourceCountry})` : sourceName;
            return (
              <option key={sourceName} value={sourceName}>{displayName}</option>
            );
          })}
        </select>
      </div>
      
      <div className="filter-group">
        <label htmlFor="days">Time Range</label>
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
      
      <div className="filter-group filter-group-country">
        <label htmlFor="countries">Country/Region</label>
        <div className="country-select-wrapper" ref={countryDropdownRef}>
          <button
            type="button"
            className="country-select-button"
            onClick={() => {
              setShowCountryDropdown(!showCountryDropdown);
              if (!showCountryDropdown) {
                setCountrySearch(''); // Clear search when opening
              }
            }}
          >
            {selectedCountriesCount > 0 
              ? `${selectedCountriesCount} selected` 
              : 'All Countries'}
          </button>
          {showCountryDropdown && (
            <div className="country-dropdown">
              <div className="country-dropdown-header">
                <span>Select Countries</span>
                {selectedCountriesCount > 0 && (
                  <button
                    type="button"
                    className="clear-countries-btn"
                    onClick={handleClearCountries}
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="country-search-wrapper">
                <input
                  type="text"
                  className="country-search-input"
                  placeholder="Type to search countries..."
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  autoFocus
                />
              </div>
              <div className="country-dropdown-list">
                {filteredCountries.length > 0 ? (
                  filteredCountries.map(country => (
                    <label key={country} className="country-checkbox-label">
                      <input
                        type="checkbox"
                        checked={(filters.countries || []).includes(country)}
                        onChange={() => handleCountryToggle(country)}
                      />
                      <span className="country-name-with-flag">
                        <span className="country-flag">{getCountryFlag(country)}</span>
                        <span className="country-name">{country}</span>
                      </span>
                    </label>
                  ))
                ) : (
                  <div className="country-no-results">No countries found</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      
      {(filters.category || filters.source || filters.search || filters.days || (filters.countries && filters.countries.length > 0)) && (
        <button
          className="clear-filters-btn"
          onClick={() => {
            onFilterChange('category', '');
            onFilterChange('source', '');
            onFilterChange('search', '');
            onFilterChange('days', '');
            onFilterChange('countries', []);
          }}
        >
          Clear Filters
        </button>
      )}
    </div>
  );
}

export default Filters;

