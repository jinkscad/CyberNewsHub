import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import './ArticleCard.css';

function ArticleCard({ article }) {
  const getCategoryColor = (category) => {
    const colors = {
      'Industry': '#00ff88',
      'Government': '#00b7ff',
      'Vendor': '#ff6b35',
      'Research': '#9d4edd'
    };
    return colors[category] || '#00ff88';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date';
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
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

