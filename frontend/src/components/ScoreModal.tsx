import type { ScoreResponse } from "../types";

type ScoreModalProps = {
  result: ScoreResponse | null;
  onClose?: () => void;
  onRestart?: () => void;
  gameOver?: boolean;
};

export function ScoreModal({ result, onClose, onRestart, gameOver = false }: ScoreModalProps) {
  if (!result) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Final score modal">
      <div className="modal-card">
        <h2>Final Score</h2>
        <p className="score-total">{result.grade}</p>
        <p className="score-subtotal">{result.totalScore} pts</p>

        <div className="score-grid">
          <div>
            <span>Production</span>
            <strong>{result.breakdown.production}</strong>
          </div>
          <div>
            <span>Awards</span>
            <strong>{result.breakdown.awards}</strong>
          </div>
          <div>
            <span>Diversity</span>
            <strong>{result.breakdown.diversity}</strong>
          </div>
          <div>
            <span>Position Fit</span>
            <strong>{result.breakdown.positionFit}</strong>
          </div>
          <div>
            <span>Completion</span>
            <strong>{result.breakdown.completionBonus}</strong>
          </div>
        </div>

        {result.penalties.length > 0 ? (
          <div className="notes-block">
            <h3>Penalties</h3>
            <ul>
              {result.penalties.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {result.warnings.length > 0 ? (
          <div className="notes-block">
            <h3>Warnings</h3>
            <ul>
              {result.warnings.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="actions-row">
          {onRestart ? (
            <button type="button" className="primary" onClick={onRestart}>
              Start Over
            </button>
          ) : null}
          {!gameOver && onClose ? (
            <button type="button" className="secondary" onClick={onClose}>
              Close
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
