import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Globe, 
  Search, 
  Newspaper, 
  BarChart3, 
  Network, 
  Settings,
  Menu,
  X,
  Activity
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import QueryPage from './pages/QueryPage';
import NewsPage from './pages/NewsPage';
import InsightsPage from './pages/InsightsPage';
import OntologyPage from './pages/OntologyPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [systemStatus, setSystemStatus] = useState(null);
  const location = useLocation();

  useEffect(() => {
    // Fetch system health status
    fetchSystemStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    const endpoint = '/health';
    try {
      const response = await fetch(endpoint, {
        headers: {
          Accept: 'application/json',
        },
      });
      const contentType = response.headers.get('content-type') || '';
      const rawBody = await response.text();

      if (!response.ok) {
        throw new Error(
          `System status request failed: ${response.status} ${response.statusText}. Raw response: ${rawBody || '<empty>'}`
        );
      }

      if (!rawBody.trim()) {
        throw new Error('System status response body is empty');
      }

      if (!contentType.includes('application/json')) {
        throw new Error(
          `Expected JSON but received "${contentType || 'unknown'}". Raw response: ${rawBody}`
        );
      }

      const data = JSON.parse(rawBody);
      setSystemStatus(data);
    } catch (error) {
      console.error('Failed to fetch system status:', {
        endpoint,
        message: error?.message || String(error),
        error,
      });
    }
  };

  const navItems = [
    { path: '/', icon: Activity, label: 'Dashboard' },
    { path: '/query', icon: Search, label: 'Query' },
    { path: '/news', icon: Newspaper, label: 'News' },
    { path: '/insights', icon: BarChart3, label: 'Insights' },
    { path: '/ontology', icon: Network, label: 'Ontology' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <Globe className="logo" size={28} />
          {sidebarOpen && (
            <motion.div 
              className="logo-text"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <h1>Global Ontology</h1>
              <span>AI-Powered Engine</span>
            </motion.div>
          )}
        </div>

        <nav className="nav">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              <item.icon size={20} />
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* System Status */}
        {sidebarOpen && systemStatus && (
          <div className="system-status">
            <div className="status-item">
              <span className={`status-dot ${systemStatus.status === 'healthy' ? 'green' : 'yellow'}`}></span>
              <span>System {systemStatus.status}</span>
            </div>
            <div className="status-item">
              <span>Neo4j: {systemStatus.services?.neo4j || 'N/A'}</span>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Top Bar */}
        <header className="topbar">
          <button 
            className="menu-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          
          <div className="topbar-title">
            <h2>
              {navItems.find(item => item.path === location.pathname)?.label || 'Dashboard'}
            </h2>
          </div>

          <div className="topbar-actions">
            <div className="live-indicator">
              <span className="pulse"></span>
              <span>Live</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="content">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/query" element={<QueryPage />} />
              <Route path="/news" element={<NewsPage />} />
              <Route path="/insights" element={<InsightsPage />} />
              <Route path="/ontology" element={<OntologyPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default App;
