import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

export default function Stage2DXO({ data }) {
  const [activeTab, setActiveTab] = useState(0);
  const critiques = Array.isArray(data) ? data : [];

  if (!critiques.length) return null;

  return (
    <div className="stage stage2">
      <div className="stage-header">
        <h3 className="stage-title">
          Stage 2: Critiques
          <span className="stage-badge">{critiques.length} critics</span>
        </h3>
      </div>

      <div className="stage-inner">
        <div className="tabs">
          {critiques.map((c, index) => (
            <button
              key={index}
              className={`tab ${activeTab === index ? 'active' : ''}`}
              onClick={() => setActiveTab(index)}
            >
              {c.model.split('/')[1] || c.model}
            </button>
          ))}
        </div>

        <div className="tab-content">
          <div className="ranking-model">{critiques[activeTab].model}</div>
          <div className="ranking-content markdown-content">
            <ReactMarkdown>{critiques[activeTab].critique || ''}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
