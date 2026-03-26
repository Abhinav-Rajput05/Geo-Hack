import React, { useMemo, useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, Clock, Tag } from 'lucide-react';
import './NewsPage.css';

const NewsPage = () => {
  const [articles, setArticles] = useState([]);
  const [sources, setSources] = useState([]);
  const [ingestionStatus, setIngestionStatus] = useState({ status: 'idle' });
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const wsRef = useRef(null);

  const categories = useMemo(() => {
    const categorySet = new Set(['all']);
    articles.forEach((article) => {
      (article.categories || []).forEach((category) => categorySet.add(category));
    });
    return Array.from(categorySet);
  }, [articles]);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [selectedCategory]);

  const normalizeArticle = (article) => {
    const categoriesFromBackend = Array.isArray(article.categories) ? article.categories : [];
    const category = article.category ? [article.category] : [];
    const categories = categoriesFromBackend.length ? categoriesFromBackend : category;

    return {
      id: article.id,
      title: article.title,
      summary: article.summary || '',
      source: article.source || 'Unknown',
      publishedAt: article.published_at || new Date().toISOString(),
      categories: categories.length ? categories : ['general'],
      sentiment: article.sentiment || 'neutral',
      relevance: Number(article.relevance_score || 0),
      url: article.url || '',
    };
  };

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [articlesRes, sourcesRes, statusRes] = await Promise.all([
        fetch('/api/v1/news/articles?limit=50'),
        fetch('/api/v1/news/sources'),
        fetch('/api/v1/news/ingestion/status'),
      ]);

      const [articlesData, sourcesData, statusData] = await Promise.all([
        articlesRes.json(),
        sourcesRes.json(),
        statusRes.json(),
      ]);

      setArticles(Array.isArray(articlesData) ? articlesData.map(normalizeArticle) : []);
      setSources(Array.isArray(sourcesData) ? sourcesData : []);
      setIngestionStatus(statusData || { status: 'idle' });
    } catch (error) {
      console.error('Failed to load news data:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const params = new URLSearchParams();
    if (selectedCategory !== 'all') {
      params.set('category', selectedCategory.toLowerCase());
    }
    const wsUrl = `${protocol}://${window.location.host}/ws/news${params.toString() ? `?${params.toString()}` : ''}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = () => {
      setWsConnected(false);
    };

    ws.onmessage = (event) => {
      try {
        const article = normalizeArticle(JSON.parse(event.data));
        setArticles((prev) => {
          if (prev.some((item) => item.id === article.id)) {
            return prev;
          }
          return [article, ...prev].slice(0, 200);
        });
      } catch (error) {
        console.error('Invalid websocket payload:', error);
      }
    };
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await fetch('/api/v1/news/ingestion/trigger', { method: 'POST' });
      await loadInitialData();
    } catch (error) {
      console.error('Failed to trigger ingestion:', error);
    } finally {
      setLoading(false);
    }
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
          <span className="stat-value">{sources.length}</span>
          <span className="stat-label">Sources</span>
        </div>
        <div className="news-stat">
          <span className="stat-value">{ingestionStatus.articles_ingested || 0}</span>
          <span className="stat-label">Ingested</span>
        </div>
        <div className="news-stat">
          <span className="stat-value status-running">
            <span className={wsConnected ? 'pulse' : ''}></span>
            {wsConnected ? 'Live' : 'Disconnected'}
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
          {sources.map((source, index) => (
            <div key={`${source.name}-${index}`} className="source-card card">
              <div className="source-header">
                <span className="source-name">{source.name}</span>
                <span className={`status-dot ${source.active ? 'green' : 'red'}`}></span>
              </div>
              <div className="source-info">
                <span className="source-type">{source.type}</span>
                <span className="source-count">{source.articles_count} articles</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default NewsPage;
