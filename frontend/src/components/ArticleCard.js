import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import './ArticleCard.css';

function ArticleCard({ article }) {
  const getCategoryClass = (category) => {
    const classes = {
      'News': 'news',
      'Research': 'research',
      'Event': 'event',
      'Alert': 'alert'
    };
    return classes[category] || 'news';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date';
    try {
      const date = new Date(dateString);
      const now = new Date();

      const diffMs = now - date;

      if (diffMs < 0) {
        const absDiff = Math.abs(diffMs);
        const diffHours = Math.floor(absDiff / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffDays > 0) {
          return `${diffDays}d ago`;
        } else if (diffHours > 0) {
          return `${diffHours}h ago`;
        } else {
          const diffMins = Math.floor(absDiff / (1000 * 60));
          return diffMins > 0 ? `${diffMins}m ago` : 'Just now';
        }
      }

      return formatDistanceToNow(date, { addSuffix: true });
    } catch {
      return 'Unknown date';
    }
  };

  const getCountries = (countryRegion) => {
    if (!countryRegion || countryRegion === 'Global') {
      return ['Global'];
    }

    const countries = countryRegion.split(',')
      .map(c => c.trim())
      .filter(c => c)
      .map(c => {
        return c.split(' ').map(word =>
          word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        ).join(' ');
      });

    const uniqueCountries = [];
    const seen = new Set();
    for (const country of countries) {
      const lower = country.toLowerCase();
      if (!seen.has(lower)) {
        seen.add(lower);
        uniqueCountries.push(country);
      }
    }

    return uniqueCountries.slice(0, 2); // Limit to 2 countries for cleaner UI
  };

  return (
    <article className="article-card">
      <div className="article-header">
        <div className="article-meta">
          <span className={`article-category ${getCategoryClass(article.category)}`}>
            {article.category || 'News'}
          </span>
          <span className="article-source">{article.source}</span>
          <span className="article-date">{formatDate(article.published_date)}</span>
        </div>
        <div className="article-meta">
          {getCountries(article.country_region).map((country, index) => (
            <span key={index} className="article-country">
              {country}
            </span>
          ))}
        </div>
      </div>
      <h2 className="article-title">
        <a
          href={article.link}
          target="_blank"
          rel="noopener noreferrer"
          className="article-link"
        >
          {article.title}
        </a>
      </h2>
      {article.description && (
        <p className="article-description">{article.description}</p>
      )}
      <a
        href={article.link}
        target="_blank"
        rel="noopener noreferrer"
        className="read-more"
      >
        Read Article
      </a>
    </article>
  );
}

export default ArticleCard;
