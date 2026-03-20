import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Newspaper, RefreshCw, Filter, ExternalLink, Clock, Tag } from 'lucide-react';
import './NewsPage.css';

const mockArticles = [
  {
    id: 1,
    title: 'Global Tech Summit Addresses AI Regulation Framework',
    summary: 'World leaders gather to discuss comprehensive frameworks for AI governance and international cooperation in technology standards.',
    source: 'BBC World',
    publishedAt: '2024-01-15T10:30:00Z',
    categories: ['Technology', 'Policy'],
    sentiment: 'neutral',
    relevance: 0.92,
  },
  {
    id: 2,
    title: 'Semiconductor Supply Chain Crisis Deepens',
    summary: 'Major chip manufacturers report ongoing supply constraints as geopolitical tensions affect global semiconductor trade routes.',
    source: 'Reuters',
    publishedAt: '2024-01-15T09:15:00Z',
    categories: ['Technology', 'Economics'],
    sentiment: 'negative',
    relevance: 0.88,
  },
  {
    id: 3,
    title: 'NATO Expansion Discussed at Brussels Summit',
    summary: 'Allied leaders meet to discuss further expansion of NATO coalition amid rising security concerns in Eastern Europe.',
    source: 'Al Jazeera',
    publishedAt: '2024-01-15T08:00:00Z',
    categories: ['Defense', 'Politics'],
    sentiment: 'neutral',
    relevance: 0.95,
  },
  {
    id: 4,
    title: 'Climate Change Impact on Agricultural Production',
    summary: 'New report details accelerating effects of climate change on global food production systems and trade patterns.',
    source: 'AP News',
    publishedAt: '2024-01-15T07:30:00Z',
    categories: ['Climate', 'Economics'],
    sentiment: 'negative',
    relevance: 0.78,
  },
  {
    id: 5,
    title: 'Renewable Energy Investments Reach Record High',
    summary: 'Global clean energy investments surge as countries accelerate transition away from fossil fuels.',
    source: 'Reuters',
    publishedAt: '2024-01-14T22:00:00Z',
    categories: ['Climate', 'Energy'],
    sentiment: 'positive',
    relevance: 0.82,
  },
];

const mockSources = [
  { name: 'BBC World', type: 'RSS', active: true, articles: 450 },
  { name: 'Reuters', type: 'RSS', active: true, articles: 380 },
  { name: 'Al Jazeera', type: 'RSS', active: true, articles: 320 },
  { name: 'NewsAPI', type: 'API', active: true, articles: 520 },
  { name: 'AP News', type: 'API', active: true, articles: 280 },
];

const NewsPage = () => {
  const [articles, setArticles] = useState(mockArticles);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const categories = ['all', 'Technology', 'Politics', 'Economics', 'Defense', 'Climate', 'Energy'];

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 2000);
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'positive': return '#10b981';
      case 'negative': return '#ef4444';
      default: return '#64748b';
    }
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));
    
    if (hours > 24) return `${Math.floor(hours / 24)}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  const filteredArticles = selectedCategory === 'all' 
    ? articles 
    : articles.filter(a => a.categories.includes(selectedCategory));

  return (
    <div className="news-page page">
      <div className="page-header">
        <h2>News Feed</h2>
        <p>Live news ingestion from multiple sources</p>
      </div>

      {/* Stats Row */}
      <div className="news-stats">
        <div className="news-stat">
          <span className="stat-value">{articles.length}</span>
          <span className="stat-label">Articles</span>
        </div>
        <div className="news-stat">
          <span className="stat-value">5</span>
          <span className="stat-label">Sources</span>
        </div>
        <div className="news-stat">
          <span className="stat-value">12</span>
          <span className="stat-label">In Queue</span>
        </div>
        <div className="news-stat">
          <span className="stat-value status-running">
            <span className="pulse"></span>
            Running
          </span>
        </div>
      </div>

      {/* Controls */}
      <div className="news-controls">
        <div className="category-filters">
          {categories.map(cat => (
            <button
              key={cat}
              className={`filter-btn ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          ))}
        </div>
        
        <button className="btn btn-primary" onClick={handleRefresh} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spinning' : ''} />
          {loading ? 'Refreshing...' : 'Refresh Feed'}
        </button>
      </div>

      {/* Articles Grid */}
      <div className="articles-grid">
        {filteredArticles.map((article, index) => (
          <motion.article 
            key={article.id}
            className="article-card card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <div className="article-header">
              <span className="article-source">{article.source}</span>
              <span className="article-time">
                <Clock size={12} />
                {formatTime(article.publishedAt)}
              </span>
            </div>
            
            <h3 className="article-title">{article.title}</h3>
            <p className="article-summary">{article.summary}</p>
            
            <div className="article-footer">
              <div className="article-tags">
                {article.categories.map(cat => (
                  <span key={cat} className="tag">
                    <Tag size={10} />
                    {cat}
                  </span>
                ))}
              </div>
              
              <div className="article-meta">
                <span 
                  className="sentiment-badge"
                  style={{ background: getSentimentColor(article.sentiment) }}
                >
                  {article.sentiment}
                </span>
                <span className="relevance">
                  {Math.round(article.relevance * 100)}% relevant
                </span>
              </div>
            </div>
          </motion.article>
        ))}
      </div>

      {/* Sources Panel */}
      <div className="sources-section">
        <h3>News Sources</h3>
        <div className="sources-grid">
          {mockSources.map((source, index) => (
            <div key={index} className="source-card card">
              <div className="source-header">
                <span className="source-name">{source.name}</span>
                <span className={`status-dot ${source.active ? 'green' : 'red'}`}></span>
              </div>
              <div className="source-info">
                <span className="source-type">{source.type}</span>
                <span className="source-count">{source.articles} articles</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default NewsPage;
