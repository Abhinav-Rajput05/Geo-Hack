import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, AlertTriangle, TrendingUp, Globe, ArrowUp, ArrowDown } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import './InsightsPage.css';

const riskByRegionData = [
  { region: 'North America', risk: 45, trend: -5 },
  { region: 'Europe', risk: 72, trend: 8 },
  { region: 'Asia Pacific', risk: 68, trend: 3 },
  { region: 'Middle East', risk: 85, trend: 12 },
  { region: 'Africa', risk: 62, trend: -2 },
  { region: 'South America', risk: 58, trend: 5 },
];

const riskByCategoryData = [
  { name: 'Geopolitical', value: 75, color: '#ef4444' },
  { name: 'Economic', value: 68, color: '#f59e0b' },
  { name: 'Defense', value: 82, color: '#ef4444' },
  { name: 'Technology', value: 71, color: '#f59e0b' },
  { name: 'Climate', value: 58, color: '#10b981' },
  { name: 'Social', value: 52, color: '#10b981' },
];

const riskTrendData = [
  { week: 'W1', geopolitical: 70, economic: 65, defense: 75, technology: 68 },
  { week: 'W2', geopolitical: 72, economic: 67, defense: 78, technology: 70 },
  { week: 'W3', geopolitical: 74, economic: 66, defense: 80, technology: 69 },
  { week: 'W4', geopolitical: 75, economic: 68, defense: 82, technology: 71 },
];

const countryRiskData = [
  { country: 'Russia', risk: 92, factor: 'Military tensions' },
  { country: 'China', risk: 88, factor: 'Trade disputes' },
  { country: 'Iran', risk: 85, factor: 'Nuclear program' },
  { country: 'North Korea', risk: 82, factor: 'Missile tests' },
  { country: 'Venezuela', risk: 78, factor: 'Economic crisis' },
  { country: 'Myanmar', risk: 75, factor: 'Political instability' },
];

const InsightsPage = () => {
  const [timeRange, setTimeRange] = useState('1M');

  return (
    <div className="insights-page page">
      <div className="page-header">
        <h2>Risk Insights</h2>
        <p>Real-time risk analysis and trend visualization</p>
      </div>

      {/* Time Range Selector */}
      <div className="time-selector">
        {['1W', '1M', '3M', '6M', '1Y'].map(range => (
          <button
            key={range}
            className={`time-btn ${timeRange === range ? 'active' : ''}`}
            onClick={() => setTimeRange(range)}
          >
            {range}
          </button>
        ))}
      </div>

      {/* Risk Overview Stats */}
      <div className="risk-overview">
        <motion.div 
          className="risk-stat-card high"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <AlertTriangle size={24} />
          <div className="risk-stat-info">
            <span className="risk-stat-value">75</span>
            <span className="risk-stat-label">Overall Risk Level</span>
          </div>
          <span className="risk-trend up">
            <ArrowUp size={14} /> +5 this week
          </span>
        </motion.div>

        <motion.div 
          className="risk-stat-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          <TrendingUp size={24} />
          <div className="risk-stat-info">
            <span className="risk-stat-value">12</span>
            <span className="risk-stat-label">Active Alerts</span>
          </div>
          <span className="risk-trend up">
            <ArrowUp size={14} /> +3 new
          </span>
        </motion.div>

        <motion.div 
          className="risk-stat-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Globe size={24} />
          <div className="risk-stat-info">
            <span className="risk-stat-value">6</span>
            <span className="risk-stat-label">High Risk Regions</span>
          </div>
          <span className="risk-trend neutral">
            No change
          </span>
        </motion.div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Risk by Region */}
        <motion.div 
          className="card chart-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="card-header">
            <h3 className="card-title">Risk by Region</h3>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={riskByRegionData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" domain={[0, 100]} stroke="#64748b" />
              <YAxis dataKey="region" type="category" width={100} stroke="#64748b" />
              <Tooltip 
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              />
              <Bar dataKey="risk" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Risk by Category (Pie) */}
        <motion.div 
          className="card chart-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="card-header">
            <h3 className="card-title">Risk by Category</h3>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={riskByCategoryData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={5}
                dataKey="value"
              >
                {riskByCategoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pie-legend">
            {riskByCategoryData.map((item, index) => (
              <div key={index} className="legend-item">
                <span className="legend-dot" style={{ background: item.color }}></span>
                <span>{item.name}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Risk Trend */}
        <motion.div 
          className="card chart-card full-width"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="card-header">
            <h3 className="card-title">Risk Trend Over Time</h3>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={riskTrendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="week" stroke="#64748b" />
              <YAxis domain={[40, 100]} stroke="#64748b" />
              <Tooltip 
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              />
              <Line type="monotone" dataKey="geopolitical" stroke="#ef4444" strokeWidth={2} />
              <Line type="monotone" dataKey="economic" stroke="#f59e0b" strokeWidth={2} />
              <Line type="monotone" dataKey="defense" stroke="#dc2626" strokeWidth={2} />
              <Line type="monotone" dataKey="technology" stroke="#8b5cf6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* High Risk Countries */}
        <motion.div 
          className="card chart-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <div className="card-header">
            <h3 className="card-title">High Risk Countries</h3>
          </div>
          <div className="country-risk-list">
            {countryRiskData.map((item, index) => (
              <div key={index} className="country-risk-item">
                <div className="country-info">
                  <span className="country-rank">#{index + 1}</span>
                  <span className="country-name">{item.country}</span>
                </div>
                <div className="country-risk-bar">
                  <div 
                    className="bar-fill" 
                    style={{ 
                      width: `${item.risk}%`,
                      background: item.risk > 80 ? '#ef4444' : item.risk > 70 ? '#f59e0b' : '#10b981'
                    }}
                  />
                </div>
                <span className="country-risk-value">{item.risk}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default InsightsPage;
