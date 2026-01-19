import ReactMarkdown from 'react-markdown';
import './Stage3.css';

export default function Stage3({ finalResponse, mode = 'council' }) {
  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage3">
      <div className="stage-header">
        <h3 className="stage-title">
          Stage 3: Final {mode === 'council' ? 'Council ' : ''}Answer
          <span className="stage-badge">Synthesized</span>
        </h3>
      </div>

      <div className="stage-inner">
        <div className="final-response">
          <div className="chairman-label">
            Chairman: {finalResponse.model.split('/')[1] || finalResponse.model}
          </div>
          <div className="final-text markdown-content">
            <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
