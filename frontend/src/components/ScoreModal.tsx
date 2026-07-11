import type { ScoreResponse } from "../types";

const SCORE_COLUMNS = [
  { key: "production", label: "Production" },
  { key: "awards", label: "Awards" },
  { key: "cups", label: "Cups" },
  { key: "grit", label: "Grit" },
  { key: "hallOfFame", label: "Hall of Fame" },
  { key: "positionFit", label: "Position Fit" },
] as const;

function getRowTotal(values: Record<(typeof SCORE_COLUMNS)[number]["key"], number>): number {
  return SCORE_COLUMNS.reduce((total, column) => total + values[column.key], 0);
}

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

        <div className="notes-block">
          <h3>How This Score Was Calculated</h3>
          <ul>
            <li>Weighted subtotal: {result.scoreSubtotal}</li>
            <li>Bonuses: +{result.bonusTotal}</li>
            <li>Hard penalties: -{result.hardPenaltyTotal}</li>
            <li>Final equation: {result.finalScoreEquation}</li>
            <li>
              Goalie quality: {result.goalieQuality} (A-floor: {result.goalieQualityFloorForA}) - {result.goalieGatePassedForA ? "A-tier eligible" : "A-tier capped"}
            </li>
          </ul>
        </div>

        <div className="score-table-wrap">
          <table className="score-table">
            <thead>
              <tr>
                <th scope="col">Weighted Contributions</th>
                {SCORE_COLUMNS.map((column) => (
                  <th key={column.key} scope="col">
                    {column.label}
                  </th>
                ))}
                <th scope="col">Goalie Quality</th>
                <th scope="col">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Weighted points</th>
                {SCORE_COLUMNS.map((column) => (
                  <td key={column.key}>{result.weightedContribution[column.key]}</td>
                ))}
                <td>{result.weightedContribution.goalieQuality}</td>
                <td>{result.scoreSubtotal}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="score-table-wrap">
          <table className="score-table">
            <thead>
              <tr>
                <th scope="col">Player</th>
                {SCORE_COLUMNS.map((column) => (
                  <th key={column.key} scope="col">
                    {column.label}
                  </th>
                ))}
                <th scope="col">Total</th>
              </tr>
            </thead>
            <tbody>
              {result.playerBreakdown.map((entry) => (
                <tr key={`${entry.slot}-${entry.playerId}`}>
                  <th scope="row">
                    <span className="score-player-name">{entry.playerName}</span>
                    <span className="score-player-slot">{entry.slot}</span>
                  </th>
                  {SCORE_COLUMNS.map((column) => (
                    <td key={column.key}>{entry.breakdown[column.key]}</td>
                  ))}
                  <td>{getRowTotal(entry.breakdown)}</td>
                </tr>
              ))}
              <tr className="score-table-total">
                <th scope="row">Totals</th>
                {SCORE_COLUMNS.map((column) => (
                  <td key={column.key}>{result.breakdown[column.key]}</td>
                ))}
                <td>{getRowTotal(result.breakdown)}</td>
              </tr>
            </tbody>
          </table>
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

        {result.penaltiesApplied.length > 0 ? (
          <div className="notes-block">
            <h3>Hard Penalty Deductions</h3>
            <ul>
              {result.penaltiesApplied.map((item) => (
                <li key={`${item.label}-${item.points}`}>
                  {item.label} (-{item.points})
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {result.bonuses.length > 0 ? (
          <div className="notes-block">
            <h3>Bonuses</h3>
            <ul>
              {result.bonuses.map((item) => (
                <li key={`${item.label}-${item.points}`}>
                  {item.label} (+{item.points})
                </li>
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
