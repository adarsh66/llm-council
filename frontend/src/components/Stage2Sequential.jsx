import './Stage2.css';
import ReactMarkdown from 'react-markdown';

export default function Stage2Sequential({ steps }) {
  const list = Array.isArray(steps) ? steps : [];
  if (!list.length) return null;

  return (
    <div className="stage stage2">
      <div className="stage-header">
        <h3 className="stage-title">
          Stage 2: Sequential Steps
          <span className="stage-badge">{list.length} steps</span>
        </h3>
      </div>
      <div className="stage-inner">
        <div className="aggregate-list">
          {list.map((item, idx) => (
            <div key={idx} className="aggregate-item">
              <span className="rank-position">Step {item.step ?? idx + 1}</span>
              <span className="rank-model">{item.model.split('/')[1] || item.model}</span>
            </div>
          ))}
        </div>
        <div className="tab-content">
          {list.map((item, idx) => (
            <div key={idx} className="ranking-content markdown-content" style={{ marginBottom: 16 }}>
              <div className="ranking-model">{item.model}</div>
              <ReactMarkdown>{item.output || ''}</ReactMarkdown>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
