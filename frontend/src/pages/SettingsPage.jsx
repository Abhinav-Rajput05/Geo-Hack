import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Key, Database, Globe, Bell, Shield, Save, RefreshCw, Trash2 } from 'lucide-react';
import './SettingsPage.css';

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('api');
  const [settings, setSettings] = useState({
    openaiKey: '',
    newsapiKey: '',
    neo4jUri: 'bolt://neo4j:7687',
    neo4jUser: 'neo4j',
    neo4jPassword: '',
    ingestionInterval: 30,
    maxArticles: 50,
    enableNotifications: true,
    emailAlerts: false,
  });

  const handleSave = () => {
    console.log('Saving settings:', settings);
    // API call to save settings
  };

  const tabs = [
    { id: 'api', label: 'API Keys', icon: Key },
    { id: 'database', label: 'Database', icon: Database },
    { id: 'ingestion', label: 'Ingestion', icon: RefreshCw },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ];

  return (
    <div className="settings-page page">
      <div className="page-header">
        <h2>Settings</h2>
        <p>Configure your Global Ontology Engine</p>
      </div>

      <div className="settings-layout">
        {/* Tabs */}
        <div className="settings-tabs">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="settings-content">
          {/* API Keys Tab */}
          {activeTab === 'api' && (
            <motion.div 
              className="settings-section"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h3>API Configuration</h3>
              
              <div className="form-group">
                <label>OpenAI API Key</label>
                <div className="input-with-action">
                  <input
                    type="password"
                    value={settings.openaiKey}
                    onChange={(e) => setSettings({...settings, openaiKey: e.target.value})}
                    placeholder="sk-..."
                  />
                  <span className="input-hint">Required for GPT-4, NER, entity linking</span>
                </div>
              </div>

              <div className="form-group">
                <label>NewsAPI Key</label>
                <div className="input-with-action">
                  <input
                    type="password"
                    value={settings.newsapiKey}
                    onChange={(e) => setSettings({...settings, newsapiKey: e.target.value})}
                    placeholder="Your NewsAPI key"
                  />
                  <span className="input-hint">Get from newsapi.org</span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Database Tab */}
          {activeTab === 'database' && (
            <motion.div 
              className="settings-section"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h3>Database Configuration</h3>
              
              <div className="form-group">
                <label>Neo4j URI</label>
                <input
                  type="text"
                  value={settings.neo4jUri}
                  onChange={(e) => setSettings({...settings, neo4jUri: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>Neo4j Username</label>
                <input
                  type="text"
                  value={settings.neo4jUser}
                  onChange={(e) => setSettings({...settings, neo4jUser: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>Neo4j Password</label>
                <input
                  type="password"
                  value={settings.neo4jPassword}
                  onChange={(e) => setSettings({...settings, neo4jPassword: e.target.value})}
                  placeholder="••••••••"
                />
              </div>

              <div className="connection-test">
                <button className="btn btn-secondary">Test Connection</button>
                <span className="connection-status success">
                  <span className="dot"></span> Connected
                </span>
              </div>
            </motion.div>
          )}

          {/* Ingestion Tab */}
          {activeTab === 'ingestion' && (
            <motion.div 
              className="settings-section"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h3>Data Ingestion Settings</h3>
              
              <div className="form-group">
                <label>Ingestion Interval (minutes)</label>
                <input
                  type="number"
                  value={settings.ingestionInterval}
                  onChange={(e) => setSettings({...settings, ingestionInterval: parseInt(e.target.value)})}
                  min={5}
                  max={120}
                />
              </div>

              <div className="form-group">
                <label>Max Articles per Cycle</label>
                <input
                  type="number"
                  value={settings.maxArticles}
                  onChange={(e) => setSettings({...settings, maxArticles: parseInt(e.target.value)})}
                  min={10}
                  max={200}
                />
              </div>

              <div className="rss-feeds-section">
                <h4>RSS Feed URLs</h4>
                <textarea
                  placeholder="Enter RSS feed URLs (one per line)"
                  rows={6}
                  defaultValue={`https://feeds.bbci.co.uk/news/world/rss.xml
https://www.reutersagency.com/feed/?taxonomy=best-topics
https://feeds.aljazeera.com/asr/home`}
                />
              </div>
            </motion.div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <motion.div 
              className="settings-section"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h3>Notification Settings</h3>
              
              <div className="toggle-group">
                <div className="toggle-item">
                  <div className="toggle-info">
                    <span className="toggle-label">Enable Notifications</span>
                    <span className="toggle-desc">Receive alerts for high-risk events</span>
                  </div>
                  <label className="toggle">
                    <input 
                      type="checkbox" 
                      checked={settings.enableNotifications}
                      onChange={(e) => setSettings({...settings, enableNotifications: e.target.checked})}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                <div className="toggle-item">
                  <div className="toggle-info">
                    <span className="toggle-label">Email Alerts</span>
                    <span className="toggle-desc">Receive email notifications</span>
                  </div>
                  <label className="toggle">
                    <input 
                      type="checkbox" 
                      checked={settings.emailAlerts}
                      onChange={(e) => setSettings({...settings, emailAlerts: e.target.checked})}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
              </div>
            </motion.div>
          )}

          {/* Save Button */}
          <div className="settings-actions">
            <button className="btn btn-primary" onClick={handleSave}>
              <Save size={16} />
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
