import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import './ArticleCard.css';

function ArticleCard({ article }) {
  const getCategoryColor = (category) => {
    const colors = {
      'News': '#00ff88',
      'Research': '#00b7ff',
      'Event': '#ff6b35',
      'Alert': '#ff4444'
    };
    return colors[category] || '#00ff88';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date';
    try {
      const date = new Date(dateString);
      const now = new Date();
      
      // Calculate time difference
      const diffMs = now - date;
      
      // If date appears to be in the future (likely timezone issue), treat it as recent
      if (diffMs < 0) {
        // Date is in future - likely timezone issue, show as "recently" or calculate backwards
        const absDiff = Math.abs(diffMs);
        const diffHours = Math.floor(absDiff / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffDays > 0) {
          return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        } else if (diffHours > 0) {
          return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        } else {
          const diffMins = Math.floor(absDiff / (1000 * 60));
          return diffMins > 0 ? `${diffMins} minute${diffMins > 1 ? 's' : ''} ago` : 'Just now';
        }
      }
      
      // Normal case: date is in the past
      return formatDistanceToNow(date, { addSuffix: true });
    } catch {
      return 'Unknown date';
    }
  };

  return (
    <article className="article-card">
      <div className="article-header">
        <div className="article-meta">
          <span
            className="article-category"
            style={{ backgroundColor: getCategoryColor(article.category) }}
          >
            {article.category || 'Uncategorized'}
          </span>
          <span className="article-source">{article.source}</span>
          <span className="article-date">{formatDate(article.published_date)}</span>
          <span className="article-country">{article.country_region || 'Global'}</span>
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
        Read Full Article →
      </a>
    </article>
  );
}

export default ArticleCard;

