# Data Build Script

This script is now a legacy fallback path and is not the primary build flow.

Run this script to generate a compact runtime data file for the backend without exposing the full `players.json` shape to the frontend.

Primary workflow: run `npm.cmd --prefix nhl-api-explorer run build-database` to generate both canonical SQLite and compact JSON artifacts directly under `backend/data/`.

Keep this script available only as an emergency rollback option during the current transition window.

## Command

```powershell
python scripts/build_data.py
```

## Output

- `backend/data/players_compact.json`

This compact file is what both backend runtime and frontend-guided gameplay are optimized for.

## Scoring Simulation Script

Use this standalone script to sample random team lineups from the game player dataset and score them with the same backend scoring logic used by the app.

This is useful for understanding score distribution, average score, grade spread, and penalty rates while tuning weights and thresholds.

### Commands

```powershell
python scripts/simulate_scoring.py --samples 10000
```

```powershell
python scripts/simulate_scoring.py --samples 25000 --seed 42 --mode realistic --json-out output/score-sim.json
```

```powershell
python scripts/simulate_scoring.py --samples 25000 --mode realistic --report-dir output/score-sim-report
```

### Modes

- `realistic` (default): fills slots as `F1,F2,F3,D1,D2,G` from player position groups.
- `random-any`: picks any 6 players and assigns them to slots, producing more off-position penalties.

### Report Bundle Output

When `--report-dir` is provided, the script writes:

- `summary.json`: full machine-readable report.
- `score_summary.csv`: key score statistics table.
- `grade_distribution.csv`: grade distribution table.
- `score_histogram.csv`: score-bin distribution table.
- `report.md`: markdown summary with tables.
- `report.html`: visual report with chart-like bars for histogram and grade distribution.

## Scoring Weight Tuning Script

Use this companion script to evaluate many SCORE_WEIGHTS configurations and rank the ones that best match a target score distribution.

Typical workflow:

1. Generate a target summary from a known-good run.
2. Run the tuner against that target with either auto-generated or custom weight sets.
3. Review the top-ranked configuration and optional JSON ranking output.

### Commands

```powershell
python scripts/simulate_scoring.py --samples 25000 --mode realistic --seed 7 --json-out output/target-distribution.json
```

```powershell
python scripts/tune_scoring_weights.py --target-json output/target-distribution.json --samples 8000 --auto-sets 120 --seed 7 --top-k 12 --json-out output/weight-tuning-ranking.json
```

### Optional Custom Weight Sets

Pass `--weight-sets-json` with one of these shapes:

```json
{
	"legacy_heavy": {
		"production": 0.28,
		"trophies": 0.2,
		"cups": 0.14,
		"grit": 0.12,
		"positionFit": 0.16,
		"hallOfFame": 0.1
	},
	"position_strict": {
		"production": 0.32,
		"trophies": 0.12,
		"cups": 0.08,
		"grit": 0.12,
		"positionFit": 0.28,
		"hallOfFame": 0.08
	}
}
```

or

```json
[
	{
		"name": "legacy_heavy",
		"weights": {
			"production": 0.28,
			"trophies": 0.2,
			"cups": 0.14,
			"grit": 0.12,
			"positionFit": 0.16,
			"hallOfFame": 0.1
		}
	}
]
```

The script normalizes each candidate so weights sum to 1.0 before scoring.
