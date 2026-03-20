import React, { useState, useEffect } from 'react';
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps';
import { motion } from 'framer-motion';
import { Globe, TrendingUp, AlertTriangle, Activity, ArrowUp, ArrowDown } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import './Dashboard.css';

const geoUrl = 'https://raw.githubusercontent.com/deldersveld/topojson/master/world-countries.json';

const mockMapData = [
  { country: 'USA', impact: 85, risk: 'medium', lat: 38.8951, lng: -77.0364 },
  { country: 'CHN', impact: 92, risk: 'high', lat: 39.9042, lng: 116.4074 },
  { country: 'RUS', impact: 78, risk: 'high', lat: 55.7558, lng: 37.6173 },
  { country: 'DEU', impact: 65, risk: 'low', lat: 52.5200, lng: 13.4050 },
  { country: 'GBR', impact: 70, risk: 'medium', lat: 51.5074, lng: -0.1278 },
  { country: 'IND', impact: 88, risk: 'medium', lat: 28.6139, lng: 77.2090 },
  { country: 'BRA', impact: 75, risk: 'medium', lat: -15.7975, lng: -47.8919 },
  { country: 'ZAF', impact: 68, risk: 'medium', lat: -25.7479, lng: 28.2293 },
  { country: 'AUS', impact: 62, risk: 'low', lat: -35.2809, lng: 149.1300 },
  { country: 'JPN', impact: 72, risk: 'low', lat: 35.6762, lng: 139.6503 },
];

const mockTrendData = [
  { time: '00:00', entities: 14500, articles: 45 },
  { time: '04:00', entities: 14520, articles: 28 },
  { time: '08:00', entities: 14680, articles: 120 },
  { time: '12:00', entities: 14850, articles: 185 },
  { time: '16:00', entities: 15000, articles: 210 },
  { time: '20:00', entities: 15080, articles: 95 },
];

const mockRiskData = [
  { category: 'Geopolitical', level: 75, trend: 'up' },
  { category: 'Economic', level: 68, trend: 'down' },
  { category: 'Defense', level: 82, trend: 'up' },
  { category: 'Technology', level: 71, trend: 'stable' },
  { category: 'Climate', level: 58, trend: 'down' },
];

const Dashboard = () => {
  const [mapData, setMapData] = useState(mockMapData);
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalEntities: 15080,
    totalRelations: 45200,
    activeSources: 8,
    articlesToday: 683,
    queriesToday: 156,
  });

  useEffect(() => {
    // Simulate loading
    setTimeout(() => setLoading(false), 1000);
    
    // Fetch real data in production
    // fetchDashboardData();
  }, []);

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'low': return '#10b981';
      default: return '#64748b';
    }
  };

  const getImpactColor = (impact) => {
    if (impact >= 80) return '#ef4444';
    if (impact >= 60) return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="dashboard page">
      {/* Stats Overview */}
      <div className="stats-grid">
        <motion.div 
          className="stat-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="stat-icon">
            <Globe size={24} />
          </div>
          <span className="stat-label">Total Entities</span>
          <span className="stat-value">{stats.totalEntities.toLocaleString()}</span>
          <span className="stat-change positive">
            <ArrowUp size={14} /> +580 today
          </span>
        </motion.div>

        <motion.div 
          className="stat-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="stat-icon">
            <Activity size={24} />
          </div>
          <span className="stat-label">Relationships</span>
          <span className="stat-value">{stats.totalRelations.toLocaleString()}</span>
          <span className="stat-change positive">
            <ArrowUp size={14} /> +1,200 today
          </span>
        </motion.div>

        <motion.div 
          className="stat-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="stat-icon">
            <TrendingUp size={24} />
          </div>
          <span className="stat-label">Articles Today</span>
          <span className="stat-value">{stats.articlesToday}</span>
          <span className="stat-change positive">
            <ArrowUp size={14} /> +45 from yesterday
          </span>
        </motion.div>

        <motion.div 
          className="stat-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="stat-icon">
            <AlertTriangle size={24} />
          </div>
          <span className="stat-label">Active Alerts</span>
          <span className="stat-value">12</span>
          <span className="stat-change negative">
            <ArrowUp size={14} /> +3 new
          </span>
        </motion.div>
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        {/* World Map */}
        <motion.div 
          className="card map-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
        >
          <div className="card-header">
            <h3 className="card-title">Global Impact Map</h3>
            <div className="map-legend">
              <span className="legend-item high">High</span>
              <span className="legend-item medium">Medium</span>
              <span className="legend-item low">Low</span>
            </div>
          </div>
          
          <div className="map-container">
            <ComposableMap 
              projection="geoMercator"
              projectionConfig={{
                scale: 140,
              }}
              style={{ width: '100%', height: '100%' }}
            >
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
                      r={impact / 10}
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
                        <rect
                          x={-50}
                          y={-45}
                          width={100}
                          height={40}
                          rx={4}
                          fill="#1e293b"
                          stroke="#334155"
                        />
                        <text
                          textAnchor="middle"
                          y={-25}
                          style={{ 
                            fontFamily: 'system-ui', 
                            fontSize: '12px', 
                            fill: '#f1f5f9',
                            fontWeight: 'bold'
                          }}
                        >
                          {country}
                        </text>
                        <text
                          textAnchor="middle"
                          y={-10}
                          style={{ 
                            fontFamily: 'system-ui', 
                            fontSize: '10px', 
                            fill: getRiskColor(risk)
                          }}
                        >
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

        {/* Trend Chart */}
        <motion.div 
          className="card trend-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6 }}
        >
          <div className="card-header">
            <h3 className="card-title">Entity Growth Trend</h3>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={mockTrendData}>
                <defs>
                  <linearGradient id="colorEntities" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    background: '#1e293b', 
                    border: '1px solid #334155',
                    borderRadius: '8px'
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="entities" 
                  stroke="#3b82f6" 
                  fillOpacity={1} 
                  fill="url(#colorEntities)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Risk Analysis */}
        <motion.div 
          className="card risk-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.7 }}
        >
          <div className="card-header">
            <h3 className="card-title">Risk Analysis by Category</h3>
          </div>
          <div className="risk-list">
            {mockRiskData.map((item, index) => (
              <div key={index} className="risk-item">
                <div className="risk-info">
                  <span className="risk-category">{item.category}</span>
                  <span className={`risk-trend ${item.trend}`}>
                    {item.trend === 'up' && <ArrowUp size={12} />}
                    {item.trend === 'down' && <ArrowDown size={12} />}
                    {item.trend === 'stable' && <span>—</span>}
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

        {/* Recent Activity */}
        <motion.div 
          className="card activity-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.8 }}
        >
          <div className="card-header">
            <h3 className="card-title">Recent Activity</h3>
          </div>
          <div className="activity-list">
            {[
              { time: '2 min ago', event: 'New entity added: "Semiconductor Alliance"', type: 'entity' },
              { time: '15 min ago', event: 'Relationship updated: USA → China (trade sanctions)', type: 'relation' },
              { time: '32 min ago', event: 'High risk alert: Energy crisis in Europe', type: 'alert' },
              { time: '1 hr ago', event: '125 articles ingested from RSS feeds', type: 'news' },
              { time: '2 hrs ago', event: 'Graph updated: +580 new nodes', type: 'update' },
            ].map((activity, index) => (
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
