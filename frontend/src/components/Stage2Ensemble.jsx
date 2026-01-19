import './Stage2.css';

export default function Stage2Ensemble({ scores }) {
  const list = Array.isArray(scores) ? scores : [];
  if (!list.length) return null;

  // Sort descending by score if present
  const sorted = [...list].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  return (
    <div className="stage stage2">
      <div className="stage-header">
        <h3 className="stage-title">
          Stage 2: Aggregation Scores
          <span className="stage-badge">{sorted.length} models</span>
        </h3>
      </div>
      <div className="stage-inner">
        <div className="aggregate-list">
          {sorted.map((item, idx) => (
            <div key={idx} className="aggregate-item">
              <span className="rank-position">#{idx + 1}</span>
              <span className="rank-model">{item.model.split('/')[1] || item.model}</span>
              <span className="rank-score">Score: {item.score ?? '—'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
