import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Send, MessageSquare, AlertCircle, CheckCircle } from 'lucide-react';
import './QueryPage.css';

const QueryPage = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([
    { id: 1, question: 'What are the current geopolitical risks in Eastern Europe?', time: '10:30 AM' },
    { id: 2, question: 'How do US-China trade tensions affect semiconductor supply chains?', time: '09:45 AM' },
    { id: 3, question: 'Which countries have the strongest military alliances?', time: 'Yesterday' },
  ]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      setResult({
        answer: "Based on the current knowledge graph, the geopolitical situation in Eastern Europe remains highly volatile. NATO expansion continues to be a key tension point, with Russia viewing it as a direct security threat. The conflict in Ukraine has led to significant shifts in military deployments and economic sanctions.",
        confidence: 0.92,
        reasoning_chain: [
          "Analyzed 1,247 related entities in the knowledge graph",
          "Identified key relationship: NATO ←→ Russia (tension level: high)",
          "Traced economic impact through trade sanctions network",
          "Cross-referenced with 45 recent news articles"
        ],
        supporting_facts: [
          { entity: 'NATO', relation: 'expanding', target: 'Eastern Europe', source: 'Reuters, Jan 2024' },
          { entity: 'Russia', relation: 'opposes', target: 'NATO expansion', source: 'Kremlin statement' },
          { entity: 'Sanctions', relation: 'affecting', target: 'Russian economy', source: 'EU report' }
        ],
        related_entities: [
          { name: 'NATO', type: 'Organization', impact: 85 },
          { name: 'Russia', type: 'Country', impact: 92 },
          { name: 'Ukraine', type: 'Country', impact: 95 },
          { name: 'United States', type: 'Country', impact: 78 }
        ]
      });
      setLoading(false);
    }, 2000);
  };

  return (
    <div className="query-page page">
      <div className="page-header">
        <h2>Ask Questions</h2>
        <p>Query the global knowledge graph using natural language</p>
      </div>

      {/* Query Input */}
      <motion.div 
        className="query-input-card card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <form onSubmit={handleSubmit} className="query-form">
          <div className="input-wrapper">
            <Search className="input-icon" size={20} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about global events, countries, organizations..."
              className="query-input"
            />
          </div>
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={loading || !query.trim()}
          >
            {loading ? (
              <>
                <span className="spinner-small" />
                Analyzing...
              </>
            ) : (
              <>
                <Send size={18} />
                Ask
              </>
            )}
          </button>
        </form>

        {/* Example Questions */}
        <div className="example-questions">
          <span className="example-label">Try:</span>
          {[
            'What is the impact of US interest rate changes on emerging markets?',
            'Which countries are most vulnerable to climate change?',
            'Explain the semiconductor supply chain dependencies'
          ].map((example, index) => (
            <button
              key={index}
              className="example-btn"
              onClick={() => setQuery(example)}
            >
              {example}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Results */}
      {result && (
        <motion.div 
          className="result-card card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="result-header">
            <MessageSquare size={20} />
            <h3>Answer</h3>
            <div className="confidence-badge">
              <CheckCircle size={14} />
              {Math.round(result.confidence * 100)}% confidence
            </div>
          </div>

          <div className="result-answer">
            {result.answer}
          </div>

          {/* Reasoning Chain */}
          <div className="reasoning-section">
            <h4>Reasoning Chain</h4>
            <div className="reasoning-steps">
              {result.reasoning_chain.map((step, index) => (
                <div key={index} className="reasoning-step">
                  <span className="step-number">{index + 1}</span>
                  <span className="step-text">{step}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Supporting Facts */}
          <div className="facts-section">
            <h4>Supporting Facts</h4>
            <div className="facts-list">
              {result.supporting_facts.map((fact, index) => (
                <div key={index} className="fact-item">
                  <AlertCircle size={14} />
                  <span>{fact.entity} {fact.relation} {fact.target}</span>
                  <span className="fact-source">{fact.source}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Related Entities */}
          <div className="entities-section">
            <h4>Related Entities</h4>
            <div className="entities-grid">
              {result.related_entities.map((entity, index) => (
                <div key={index} className="entity-chip">
                  <span className="entity-name">{entity.name}</span>
                  <span className="entity-type">{entity.type}</span>
                  <span className="entity-impact" style={{ 
                    color: entity.impact > 80 ? '#ef4444' : entity.impact > 60 ? '#f59e0b' : '#10b981' 
                  }}>
                    {entity.impact}% impact
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Query History */}
      <div className="history-section">
        <h3>Recent Queries</h3>
        <div className="history-list">
          {history.map((item) => (
            <div 
              key={item.id} 
              className="history-item"
              onClick={() => setQuery(item.question)}
            >
              <MessageSquare size={16} />
              <span className="history-question">{item.question}</span>
              <span className="history-time">{item.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default QueryPage;
