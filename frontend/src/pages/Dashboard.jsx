import React, { useState, useEffect } from 'react';
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps';
import { motion } from 'framer-motion';
import { Globe, TrendingUp, AlertTriangle, Activity, ArrowUp, ArrowDown } from 'lucide-react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import './Dashboard.css';

const geoUrl = 'https://raw.githubusercontent.com/deldersveld/topojson/master/world-countries.json';

const Dashboard = () => {
  const [mapData, setMapData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [riskData, setRiskData] = useState([]);
  const [activityData, setActivityData] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    totalEntities: 0,
    totalRelations: 0,
    activeSources: 0,
    articlesToday: 0,
    queriesToday: 0,
    activeAlerts: 0,
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError('');

    try {
      const [
        ontologyRes,
        riskRes,
        mapRes,
        newsRes,
        newsSourcesRes,
        suggestionsRes
      ] = await Promise.all([
        fetch('/api/v1/ontology/stats'),
        fetch('/api/v1/insights/risk-analysis?detailed=true'),
        fetch('/api/v1/insights/map-data'),
        fetch('/api/v1/news/articles?limit=20'),
        fetch('/api/v1/news/sources'),
        fetch('/api/v1/query/suggestions?prefix=global&limit=5'),
      ]);

      const [
        ontology,
        riskPayload,
        mapPayload,
        newsArticles,
        newsSources,
        querySuggestions
      ] = await Promise.all([
        ontologyRes.json(),
        riskRes.json(),
        mapRes.json(),
        newsRes.json(),
        newsSourcesRes.json(),
        suggestionsRes.json(),
      ]);

      const categories = riskPayload.full?.categories || [];
      const weekly = riskPayload.full?.trends?.weekly || [];

      const mappedTrendData = weekly.map((item, idx) => {
        const aggregate = Object.entries(item)
          .filter(([key]) => key !== 'week')
          .reduce((sum, [, value]) => sum + Number(value || 0), 0);

        return {
          time: item.week || `W${idx + 1}`,
          entities: Number(ontology.total_nodes || 0),
          articles: aggregate,
        };
      });

      const mappedMapData = (mapPayload.countries || []).map((country) => ({
        country: country.code || country.name || 'UNK',
        impact: Number(country.impact ?? country.value ?? 0),
        risk: Number(country.impact ?? country.value ?? 0) > 70 ? 'high' : Number(country.impact ?? country.value ?? 0) > 45 ? 'medium' : 'low',
        lat: Number(country.lat || 0),
        lng: Number(country.lng || 0),
      }));

      const mappedRiskData = categories.map((item) => ({
        category: item.category,
        level: Number(item.level || 0),
        trend: item.trend || 'stable',
      }));

      const todayDate = new Date().toISOString().slice(0, 10);
      const articlesToday = (newsArticles || []).filter((article) =>
        String(article.published_at || '').startsWith(todayDate)
      ).length;

      const activity = (newsArticles || []).slice(0, 5).map((article, idx) => ({
        time: article.published_at || 'recent',
        event: article.title || 'News update',
        type: idx % 2 === 0 ? 'news' : 'update',
      }));

      setMapData(mappedMapData);
      setTrendData(mappedTrendData);
      setRiskData(mappedRiskData);
      setActivityData(activity);
      setStats({
        totalEntities: Number(ontology.total_nodes || 0),
        totalRelations: Number(ontology.total_relationships || 0),
        activeSources: Array.isArray(newsSources) ? newsSources.length : 0,
        articlesToday,
        queriesToday: querySuggestions?.suggestions?.length || 0,
        activeAlerts: mappedRiskData.filter((risk) => risk.level >= 70).length,
      });
    } catch (fetchError) {
      setError('Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'low': return '#10b981';
      default: return '#64748b';
    }
  };

  return (
    <div className="dashboard page">
      {loading && <div className="card">Loading dashboard data...</div>}
      {error && <div className="card" style={{ color: '#ef4444' }}>{error}</div>}

      <div className="stats-grid">
        <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <div className="stat-icon"><Globe size={24} /></div>
          <span className="stat-label">Total Entities</span>
          <span className="stat-value">{stats.totalEntities.toLocaleString()}</span>
          <span className="stat-change positive"><ArrowUp size={14} /> live</span>
        </motion.div>

        <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <div className="stat-icon"><Activity size={24} /></div>
          <span className="stat-label">Relationships</span>
          <span className="stat-value">{stats.totalRelations.toLocaleString()}</span>
          <span className="stat-change positive"><ArrowUp size={14} /> live</span>
        </motion.div>

        <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="stat-icon"><TrendingUp size={24} /></div>
          <span className="stat-label">Articles Today</span>
          <span className="stat-value">{stats.articlesToday}</span>
          <span className="stat-change positive"><ArrowUp size={14} /> rolling</span>
        </motion.div>

        <motion.div className="stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          <div className="stat-icon"><AlertTriangle size={24} /></div>
          <span className="stat-label">Active Alerts</span>
          <span className="stat-value">{stats.activeAlerts}</span>
          <span className="stat-change negative"><ArrowUp size={14} /> risk based</span>
        </motion.div>
      </div>

      <div className="dashboard-grid">
        <motion.div className="card map-card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.5 }}>
          <div className="card-header">
            <h3 className="card-title">Global Impact Map</h3>
            <div className="map-legend">
              <span className="legend-item high">High</span>
              <span className="legend-item medium">Medium</span>
              <span className="legend-item low">Low</span>
            </div>
          </div>

          <div className="map-container">
            <ComposableMap projection="geoMercator" projectionConfig={{ scale: 140 }} style={{ width: '100%', height: '100%' }}>
              <ZoomableGroup center={[0, 20]} zoom={1}>
                <Geographies geography={geoUrl}>
                  {({ geographies }) =>
                    geographies.map((geo) => (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill="#1e293b"
                        stroke="#334155"
                        strokeWidth={0.5}
                        style={{
                          default: { outline: 'none' },
                          hover: { fill: '#334155', outline: 'none' },
                          pressed: { fill: '#475569', outline: 'none' },
                        }}
                      />
                    ))
                  }
                </Geographies>

                {mapData.map(({ country, impact, risk, lat, lng }) => (
                  <Marker key={country} coordinates={[lng, lat]}>
                    <circle
                      r={Math.max(2, impact / 10)}
                      fill={getRiskColor(risk)}
                      fillOpacity={0.6}
                      stroke={getRiskColor(risk)}
                      strokeWidth={2}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setSelectedCountry(country)}
                      onMouseLeave={() => setSelectedCountry(null)}
                    />
                    {selectedCountry === country && (
                      <g>
                        <rect x={-50} y={-45} width={100} height={40} rx={4} fill="#1e293b" stroke="#334155" />
                        <text textAnchor="middle" y={-25} style={{ fontFamily: 'system-ui', fontSize: '12px', fill: '#f1f5f9', fontWeight: 'bold' }}>
                          {country}
                        </text>
                        <text textAnchor="middle" y={-10} style={{ fontFamily: 'system-ui', fontSize: '10px', fill: getRiskColor(risk) }}>
                          Impact: {impact}%
                        </text>
                      </g>
                    )}
                  </Marker>
                ))}
              </ZoomableGroup>
            </ComposableMap>
          </div>
        </motion.div>

        <motion.div className="card trend-card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.6 }}>
          <div className="card-header">
            <h3 className="card-title">Entity Growth Trend</h3>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="colorEntities" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="entities" stroke="#3b82f6" fillOpacity={1} fill="url(#colorEntities)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div className="card risk-card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.7 }}>
          <div className="card-header">
            <h3 className="card-title">Risk Analysis by Category</h3>
          </div>
          <div className="risk-list">
            {riskData.map((item, index) => (
              <div key={index} className="risk-item">
                <div className="risk-info">
                  <span className="risk-category">{item.category}</span>
                  <span className={`risk-trend ${item.trend}`}>
                    {item.trend === 'up' && <ArrowUp size={12} />}
                    {item.trend === 'down' && <ArrowDown size={12} />}
                    {item.trend === 'stable' && <span>-</span>}
                  </span>
                </div>
                <div className="risk-bar-container">
                  <div
                    className="risk-bar"
                    style={{
                      width: `${item.level}%`,
                      background: item.level > 70 ? '#ef4444' : item.level > 50 ? '#f59e0b' : '#10b981'
                    }}
                  />
                </div>
                <span className="risk-value">{item.level}%</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div className="card activity-card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.8 }}>
          <div className="card-header">
            <h3 className="card-title">Recent Activity</h3>
          </div>
          <div className="activity-list">
            {activityData.map((activity, index) => (
              <div key={index} className="activity-item">
                <div className={`activity-dot ${activity.type}`} />
                <div className="activity-content">
                  <span className="activity-event">{activity.event}</span>
                  <span className="activity-time">{activity.time}</span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;
