import React from 'react';
import ArticleCard from './ArticleCard';
import './ArticleList.css';

function ArticleList({ articles }) {
  if (articles.length === 0) {
    return (
      <div className="no-articles">
        <p>No articles found. Try adjusting your filters or fetch the latest news!</p>
      </div>
    );
  }

  return (
    <div className="article-list">
      {articles.map(article => (
        <ArticleCard key={article.id} article={article} />
      ))}
    </div>
  );
}

export default ArticleList;

