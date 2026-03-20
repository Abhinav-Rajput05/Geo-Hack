import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Network, Search, Filter, ChevronRight, Users, Building, Globe as GlobeIcon, Briefcase, Cpu, Calendar } from 'lucide-react';
import './OntologyPage.css';

const entityTypes = [
  { type: 'Country', icon: GlobeIcon, count: 195, color: '#3b82f6' },
  { type: 'Organization', icon: Building, count: 850, color: '#8b5cf6' },
  { type: 'Company', icon: Briefcase, count: 2500, color: '#10b981' },
  { type: 'Individual', icon: Users, count: 5000, color: '#f59e0b' },
  { type: 'System', icon: Cpu, count: 1200, color: '#ef4444' },
  { type: 'Event', icon: Calendar, count: 5255, color: '#ec4899' },
];

const relationshipTypes = [
  { type: 'alliesWith', count: 450, description: 'Formal alliance or partnership' },
  { type: 'tradesWith', count: 2800, description: 'Trade relationship' },
  { type: 'sanctions', count: 120, description: 'Sanctions imposed' },
  { type: 'supplies', count: 1500, description: 'Supply chain relationship' },
  { type: 'dependsOn', count: 3200, description: 'Critical dependency' },
  { type: 'competesWith', count: 890, description: 'Competitive relationship' },
  { type: 'influences', count: 2100, description: 'Political/economic influence' },
];

const mockEntities = [
  { id: 'ent_001', name: 'United States', type: 'Country', relations: 125 },
  { id: 'ent_002', name: 'China', type: 'Country', relations: 118 },
  { id: 'ent_003', name: 'NATO', type: 'Organization', relations: 89 },
  { id: 'ent_004', name: 'European Union', type: 'Organization', relations: 156 },
  { id: 'ent_005', name: 'Apple Inc', type: 'Company', relations: 45 },
];

const OntologyPage = () => {
  const [selectedType, setSelectedType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="ontology-page page">
      <div className="page-header">
        <h2>Knowledge Graph</h2>
        <p>Explore the ontology structure and entities</p>
      </div>

      {/* Entity Types Overview */}
      <div className="entity-types-grid">
        {entityTypes.map((item, index) => (
          <motion.div
            key={item.type}
            className={`entity-type-card card ${selectedType === item.type ? 'selected' : ''}`}
            onClick={() => setSelectedType(selectedType === item.type ? 'all' : item.type)}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <div className="entity-type-icon" style={{ background: `${item.color}20`, color: item.color }}>
              <item.icon size={24} />
            </div>
            <div className="entity-type-info">
              <span className="entity-type-name">{item.type}</span>
              <span className="entity-type-count">{item.count.toLocaleString()}</span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Graph Stats */}
      <div className="graph-stats card">
        <div className="stat">
          <span className="stat-value">15,000</span>
          <span className="stat-label">Total Nodes</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat">
          <span className="stat-value">45,000</span>
          <span className="stat-label">Total Relationships</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat">
          <span className="stat-value">7</span>
          <span className="stat-label">Entity Types</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat">
          <span className="stat-value">7</span>
          <span className="stat-label">Relationship Types</span>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="ontology-controls">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search entities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button className="btn btn-secondary">
          <Filter size={16} />
          Filters
        </button>
      </div>

      {/* Relationship Types */}
      <div className="section">
        <h3>Relationship Types</h3>
        <div className="relationships-grid">
          {relationshipTypes.map((rel, index) => (
            <div key={index} className="relationship-card card">
              <div className="rel-header">
                <span className="rel-type">{rel.type}</span>
                <span className="rel-count">{rel.count}</span>
              </div>
              <p className="rel-description">{rel.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Entity Browser */}
      <div className="section">
        <h3>Browse Entities</h3>
        <div className="entities-list">
          {mockEntities.map((entity, index) => (
            <motion.div
              key={entity.id}
              className="entity-row card"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <div className="entity-icon">
                {entity.type === 'Country' && <GlobeIcon size={18} />}
                {entity.type === 'Organization' && <Building size={18} />}
                {entity.type === 'Company' && <Briefcase size={18} />}
              </div>
              <div className="entity-details">
                <span className="entity-name">{entity.name}</span>
                <span className="entity-type-label">{entity.type}</span>
              </div>
              <div className="entity-relations">
                <span>{entity.relations} relations</span>
              </div>
              <ChevronRight size={18} className="chevron" />
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default OntologyPage;
