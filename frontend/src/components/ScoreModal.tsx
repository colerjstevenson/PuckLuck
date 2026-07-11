import type { ScoreResponse } from "../types";

const SCORE_COLUMNS = [
  { key: "production", label: "Production" },
  { key: "awards", label: "Awards" },
  { key: "cups", label: "Cups" },
  { key: "grit", label: "Grit" },
  { key: "hallOfFame", label: "Hall of Fame" },
  { key: "positionFit", label: "Position Fit" },
] as const;

const SCORE_WEIGHTS: Record<(typeof SCORE_COLUMNS)[number]["key"], number> = {
  production: 0.25,
  awards: 0.15,
  cups: 0.2,
  grit: 0.1,
  hallOfFame: 0.1,
  positionFit: 0.35,
};

const GRADE_THRESHOLDS: Array<[number, string]> = [
  [96, "A++"],
  [80, "A+"],
  [74, "A"],
  [70, "A-"],
  [66, "B+"],
  [62, "B"],
  [58, "B-"],
  [54, "C+"],
  [50, "C"],
  [46, "C-"],
  [40, "D+"],
  [35, "D"],
  [30, "D-"],
  [0, "F"],
];

const BOOLEAN_SCORE_COLUMNS = new Set<"hallOfFame" | "positionFit">(["hallOfFame", "positionFit"]);

function toGrade(score: number): string {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  for (const [threshold, label] of GRADE_THRESHOLDS) {
    if (clamped >= threshold) {
      return label;
    }
  }
  return "F";
}

function toSignedGrade(score: number): string {
  if (score === 0) {
    return toGrade(0);
  }
  const sign = score > 0 ? "+" : "-";
  return `${sign}${toGrade(Math.abs(score))}`;
}

function weightedPointsForCategory(
  values: Record<(typeof SCORE_COLUMNS)[number]["key"], number>,
  key: (typeof SCORE_COLUMNS)[number]["key"],
): number {
  return values[key] * SCORE_WEIGHTS[key];
}

function getWeightedRowTotal(values: Record<(typeof SCORE_COLUMNS)[number]["key"], number>): number {
  return SCORE_COLUMNS.reduce((total, column) => total + weightedPointsForCategory(values, column.key), 0);
}

function formatPoints(points: number): string {
  const rounded = Math.round(points * 10) / 10;
  return `${rounded.toFixed(1).replace(/\.0$/, "")} pts`;
}

function renderPlayerCategoryCell(
  values: Record<(typeof SCORE_COLUMNS)[number]["key"], number>,
  key: (typeof SCORE_COLUMNS)[number]["key"],
): string {
  if (BOOLEAN_SCORE_COLUMNS.has(key as "hallOfFame" | "positionFit")) {
    return values[key] > 0 ? "✓" : "X";
  }

  return formatPoints(weightedPointsForCategory(values, key));
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
                <th scope="col">Weighted Total</th>
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
                    <td key={column.key}>{renderPlayerCategoryCell(entry.breakdown, column.key)}</td>
                  ))}
                  <td>{formatPoints(getWeightedRowTotal(entry.breakdown))}</td>
                </tr>
              ))}
              <tr className="score-table-total">
                <th scope="row">Lineup Weighted</th>
                {SCORE_COLUMNS.map((column) => (
                  <td key={column.key}>{formatPoints(result.weightedContribution[column.key])}</td>
                ))}
                <td>
                  {formatPoints(
                    SCORE_COLUMNS.reduce(
                      (total, column) => total + result.weightedContribution[column.key],
                      0,
                    ),
                  )}
                </td>
              </tr>
              <tr className="score-table-total">
                <th scope="row">Goalie Quality</th>
                <td colSpan={SCORE_COLUMNS.length}>Weighted goalie quality contribution</td>
                <td>{formatPoints(result.weightedContribution.goalieQuality)}</td>
              </tr>
              <tr className="score-table-total">
                <th scope="row">Score Subtotal</th>
                <td colSpan={SCORE_COLUMNS.length}>Weighted total before hard penalties</td>
                <td>{formatPoints(result.scoreSubtotal)}</td>
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
                  {item.label} ({toSignedGrade(-item.points)})
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
                  {item.label} ({toSignedGrade(item.points)})
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
