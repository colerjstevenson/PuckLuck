from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.game_service import load_players, score_lineup  # type: ignore[import-not-found]  # noqa: E402

SLOTS = ["F1", "F2", "F3", "D1", "D2", "G"]
SLOT_GROUPS = {
    "F1": "Forward",
    "F2": "Forward",
    "F3": "Forward",
    "D1": "Defense",
    "D2": "Defense",
    "G": "Goalie",
}

GRADE_ORDER = [
    "A++",
    "A+",
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "D+",
    "D",
    "D-",
    "F",
]

MIN_GAMES_PLAYED = 100


def _pct(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (count / total) * 100.0


def _percentile(values: list[int], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    index = (len(ordered) - 1) * p
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return float(ordered[low])
    frac = index - low
    return ordered[low] + ((ordered[high] - ordered[low]) * frac)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_lineup_realistic(pools: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    forwards = random.sample(pools["Forward"], 3)
    defense = random.sample(pools["Defense"], 2)
    goalie = random.choice(pools["Goalie"])

    picked = {
        "F1": forwards[0],
        "F2": forwards[1],
        "F3": forwards[2],
        "D1": defense[0],
        "D2": defense[1],
        "G": goalie,
    }

    return [{"slot": slot, "playerId": picked[slot]["id"]} for slot in SLOTS]


def _build_lineup_random_any(players: list[dict[str, Any]]) -> list[dict[str, str]]:
    selected = random.sample(players, len(SLOTS))
    return [{"slot": slot, "playerId": selected[i]["id"]} for i, slot in enumerate(SLOTS)]


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [item["totalScore"] for item in results]
    penalties_per_lineup = [len(item["penalties"]) for item in results]
    warnings_per_lineup = [len(item["warnings"]) for item in results]

    histogram: dict[str, int] = {}
    for start in range(0, 100, 10):
        end = start + 9
        key = f"{start:02d}-{end:02d}"
        histogram[key] = 0
    histogram["100"] = 0

    for score in scores:
        if score == 100:
            histogram["100"] += 1
        else:
            bucket_start = (score // 10) * 10
            bucket_end = bucket_start + 9
            histogram[f"{bucket_start:02d}-{bucket_end:02d}"] += 1

    grade_counter = Counter(item["grade"] for item in results)

    return {
        "lineups": len(results),
        "score": {
            "mean": round(statistics.fmean(scores), 2),
            "median": round(statistics.median(scores), 2),
            "stdev": round(statistics.pstdev(scores), 2),
            "min": min(scores),
            "p10": round(_percentile(scores, 0.10), 2),
            "p25": round(_percentile(scores, 0.25), 2),
            "p75": round(_percentile(scores, 0.75), 2),
            "p90": round(_percentile(scores, 0.90), 2),
            "max": max(scores),
        },
        "penalties": {
            "lineupsWithPenalties": sum(1 for count in penalties_per_lineup if count > 0),
            "avgPenaltiesPerLineup": round(statistics.fmean(penalties_per_lineup), 3),
        },
        "warnings": {
            "lineupsWithWarnings": sum(1 for count in warnings_per_lineup if count > 0),
            "avgWarningsPerLineup": round(statistics.fmean(warnings_per_lineup), 3),
        },
        "grades": {grade: grade_counter.get(grade, 0) for grade in GRADE_ORDER if grade_counter.get(grade, 0) > 0},
        "histogram": histogram,
    }


def _lineup_to_names(lineup: list[dict[str, str]], players_by_id: dict[str, dict[str, Any]]) -> dict[str, str]:
    named: dict[str, str] = {}
    for pick in lineup:
        slot = pick["slot"]
        player = players_by_id.get(pick["playerId"])
        named[slot] = player.get("name", pick["playerId"]) if player else pick["playerId"]
    return named


def run_simulation(samples: int, mode: str, seed: int | None = None) -> dict[str, Any]:
    if seed is not None:
        random.seed(seed)

    players = load_players()
    if not players:
        raise RuntimeError("No players loaded. Ensure backend/data has generated player data.")

    eligible_players = [
        player
        for player in players
        if _as_int(player.get("stats", {}).get("gamesPlayed"), 0) >= MIN_GAMES_PLAYED
    ]
    if not eligible_players:
        raise RuntimeError(
            f"No players meet minimum games requirement (>= {MIN_GAMES_PLAYED} games played)."
        )

    players_by_id = {player["id"]: player for player in eligible_players}
    pools = {
        "Forward": [p for p in eligible_players if p.get("positionGroup") == "Forward"],
        "Defense": [p for p in eligible_players if p.get("positionGroup") == "Defense"],
        "Goalie": [p for p in eligible_players if p.get("positionGroup") == "Goalie"],
    }

    if mode == "realistic":
        if len(pools["Forward"]) < 3 or len(pools["Defense"]) < 2 or len(pools["Goalie"]) < 1:
            raise RuntimeError("Not enough players by position group to sample realistic lineups.")
    elif len(eligible_players) < len(SLOTS):
        raise RuntimeError(
            f"Need at least {len(SLOTS)} eligible players for random-any mode after filtering by games played."
        )

    results: list[dict[str, Any]] = []

    for _ in range(samples):
        if mode == "realistic":
            lineup = _build_lineup_realistic(pools)
        else:
            lineup = _build_lineup_random_any(eligible_players)

        score = score_lineup(lineup)
        results.append(
            {
                "lineup": lineup,
                "totalScore": score["totalScore"],
                "grade": score["grade"],
                "penalties": score["penalties"],
                "warnings": score["warnings"],
                "breakdown": score["breakdown"],
            }
        )

    summary = _summarize(results)
    top = sorted(results, key=lambda item: item["totalScore"], reverse=True)[:5]
    bottom = sorted(results, key=lambda item: item["totalScore"])[:5]

    return {
        "settings": {"samples": samples, "mode": mode, "seed": seed},
        "playerPool": {
            "total": len(eligible_players),
            "forwards": len(pools["Forward"]),
            "defense": len(pools["Defense"]),
            "goalies": len(pools["Goalie"]),
        },
        "summary": summary,
        "topExamples": [
            {
                "score": item["totalScore"],
                "grade": item["grade"],
                "lineup": _lineup_to_names(item["lineup"], players_by_id),
            }
            for item in top
        ],
        "bottomExamples": [
            {
                "score": item["totalScore"],
                "grade": item["grade"],
                "lineup": _lineup_to_names(item["lineup"], players_by_id),
            }
            for item in bottom
        ],
    }


def _print_report(report: dict[str, Any]) -> None:
    settings = report["settings"]
    pool = report["playerPool"]
    summary = report["summary"]
    score_stats = summary["score"]

    print("== Scoring Simulation ==")
    print(f"Samples: {settings['samples']}")
    print(f"Mode: {settings['mode']}")
    print(f"Seed: {settings['seed'] if settings['seed'] is not None else 'random'}")
    print(
        "Player pool: "
        f"{pool['total']} total "
        f"(F={pool['forwards']}, D={pool['defense']}, G={pool['goalies']})"
    )
    print()

    print("Score distribution")
    print(f"  mean={score_stats['mean']}")
    print(f"  median={score_stats['median']}")
    print(f"  stdev={score_stats['stdev']}")
    print(f"  min={score_stats['min']}  p10={score_stats['p10']}  p25={score_stats['p25']}")
    print(f"  p75={score_stats['p75']}  p90={score_stats['p90']}  max={score_stats['max']}")
    print()

    penalties = summary["penalties"]
    warnings = summary["warnings"]
    lineups = summary["lineups"]

    penalty_rate = (penalties["lineupsWithPenalties"] / lineups) * 100
    warning_rate = (warnings["lineupsWithWarnings"] / lineups) * 100

    print("Penalties / warnings")
    print(
        "  penalties: "
        f"{penalties['lineupsWithPenalties']}/{lineups} ({penalty_rate:.1f}%), "
        f"avg={penalties['avgPenaltiesPerLineup']}"
    )
    print(
        "  warnings: "
        f"{warnings['lineupsWithWarnings']}/{lineups} ({warning_rate:.1f}%), "
        f"avg={warnings['avgWarningsPerLineup']}"
    )
    print()

    print("Grades")
    for grade in GRADE_ORDER:
        count = summary["grades"].get(grade)
        if count:
            pct = (count / lineups) * 100
            print(f"  {grade:>3}: {count:>6} ({pct:5.1f}%)")
    print()

    print("Histogram (score bins)")
    max_bucket = max(summary["histogram"].values()) if summary["histogram"] else 1
    for label, count in summary["histogram"].items():
        bar_len = int((count / max_bucket) * 30) if max_bucket else 0
        bar = "#" * bar_len
        print(f"  {label:>5}: {count:>6} {bar}")
    print()

    print("Top examples")
    for idx, item in enumerate(report["topExamples"], start=1):
        lineup = ", ".join(f"{slot}:{name}" for slot, name in item["lineup"].items())
        print(f"  {idx}. {item['score']} ({item['grade']}): {lineup}")
    print()

    print("Bottom examples")
    for idx, item in enumerate(report["bottomExamples"], start=1):
        lineup = ", ".join(f"{slot}:{name}" for slot, name in item["lineup"].items())
        print(f"  {idx}. {item['score']} ({item['grade']}): {lineup}")


def _write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)]
    for row in rows:
        cells = []
        for cell in row:
            text = str(cell)
            if "," in text or "\"" in text or "\n" in text:
                text = '"' + text.replace('"', '""') + '"'
            cells.append(text)
        lines.append(",".join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_markdown_report(report: dict[str, Any]) -> str:
    settings = report["settings"]
    summary = report["summary"]
    score = summary["score"]
    total = summary["lineups"]

    lines: list[str] = []
    lines.append("# Scoring Simulation Report")
    lines.append("")
    lines.append("## Settings")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---:|")
    lines.append(f"| samples | {settings['samples']} |")
    lines.append(f"| mode | {settings['mode']} |")
    lines.append(f"| seed | {settings['seed'] if settings['seed'] is not None else 'random'} |")
    lines.append("")
    lines.append("## Score Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key in ["mean", "median", "stdev", "min", "p10", "p25", "p75", "p90", "max"]:
        lines.append(f"| {key} | {score[key]} |")
    lines.append("")
    lines.append("## Grade Distribution")
    lines.append("")
    lines.append("| Grade | Count | Percent |")
    lines.append("|---|---:|---:|")
    for grade in GRADE_ORDER:
        count = summary["grades"].get(grade, 0)
        if count <= 0:
            continue
        lines.append(f"| {grade} | {count} | {_pct(count, total):.2f}% |")
    lines.append("")
    lines.append("## Histogram")
    lines.append("")
    lines.append("| Score Bin | Count | Percent |")
    lines.append("|---|---:|---:|")
    for bucket, count in summary["histogram"].items():
        lines.append(f"| {bucket} | {count} | {_pct(count, total):.2f}% |")
    lines.append("")
    lines.append("## Top Examples")
    lines.append("")
    lines.append("| Rank | Score | Grade | Lineup |")
    lines.append("|---:|---:|---:|---|")
    for idx, item in enumerate(report["topExamples"], start=1):
        lineup = "; ".join(f"{slot}:{name}" for slot, name in item["lineup"].items())
        lines.append(f"| {idx} | {item['score']} | {item['grade']} | {lineup} |")
    lines.append("")
    lines.append("## Bottom Examples")
    lines.append("")
    lines.append("| Rank | Score | Grade | Lineup |")
    lines.append("|---:|---:|---:|---|")
    for idx, item in enumerate(report["bottomExamples"], start=1):
        lineup = "; ".join(f"{slot}:{name}" for slot, name in item["lineup"].items())
        lines.append(f"| {idx} | {item['score']} | {item['grade']} | {lineup} |")

    return "\n".join(lines) + "\n"


def _build_html_report(report: dict[str, Any]) -> str:
    settings = report["settings"]
    summary = report["summary"]
    score = summary["score"]
    total = summary["lineups"]

    hist_rows: list[str] = []
    hist_max = max(summary["histogram"].values()) if summary["histogram"] else 1
    for bucket, count in summary["histogram"].items():
        width = 0 if hist_max == 0 else (count / hist_max) * 100.0
        hist_rows.append(
            "<tr>"
            f"<td>{bucket}</td>"
            f"<td>{count}</td>"
            f"<td>{_pct(count, total):.2f}%</td>"
            f"<td><div class=\"bar\"><span style=\"width:{width:.2f}%\"></span></div></td>"
            "</tr>"
        )

    grade_rows: list[str] = []
    grade_max = max(summary["grades"].values()) if summary["grades"] else 1
    for grade in GRADE_ORDER:
        count = summary["grades"].get(grade, 0)
        if count <= 0:
            continue
        width = 0 if grade_max == 0 else (count / grade_max) * 100.0
        grade_rows.append(
            "<tr>"
            f"<td>{grade}</td>"
            f"<td>{count}</td>"
            f"<td>{_pct(count, total):.2f}%</td>"
            f"<td><div class=\"bar\"><span style=\"width:{width:.2f}%\"></span></div></td>"
            "</tr>"
        )

    def _examples_table(examples: list[dict[str, Any]]) -> str:
        rows = []
        for idx, item in enumerate(examples, start=1):
            lineup = ", ".join(f"{slot}:{name}" for slot, name in item["lineup"].items())
            rows.append(
                "<tr>"
                f"<td>{idx}</td><td>{item['score']}</td><td>{item['grade']}</td><td>{lineup}</td>"
                "</tr>"
            )
        return "".join(rows)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Scoring Simulation Report</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --ink: #10233f;
      --muted: #5d708f;
      --line: #dce4f0;
      --accent: #0b7fab;
      --accent-soft: #d8eef6;
    }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 10% 0%, #e7f3ff 0%, var(--bg) 45%);
      color: var(--ink);
      font-family: Segoe UI, Tahoma, Geneva, Verdana, sans-serif;
    }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px; }}
    h1, h2 {{ margin: 0 0 12px 0; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 19px; margin-top: 16px; }}
    p {{ margin: 0 0 6px 0; color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; font-size: 14px; vertical-align: top; }}
    th {{ background: #eef3fa; }}
    tr:last-child td {{ border-bottom: none; }}
    .bar {{ height: 12px; background: var(--accent-soft); border-radius: 99px; overflow: hidden; min-width: 120px; }}
    .bar > span {{ display: block; height: 100%; background: linear-gradient(90deg, #25a9d8, var(--accent)); }}
    .mono {{ font-family: Consolas, 'Courier New', monospace; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Scoring Simulation Report</h1>
    <p>Samples: <span class=\"mono\">{settings['samples']}</span> | Mode: <span class=\"mono\">{settings['mode']}</span> | Seed: <span class=\"mono\">{settings['seed'] if settings['seed'] is not None else 'random'}</span></p>

    <h2>Score Summary</h2>
    <div class=\"grid\">
      <div class=\"card\"><strong>Mean</strong><p class=\"mono\">{score['mean']}</p></div>
      <div class=\"card\"><strong>Median</strong><p class=\"mono\">{score['median']}</p></div>
      <div class=\"card\"><strong>Std Dev</strong><p class=\"mono\">{score['stdev']}</p></div>
      <div class=\"card\"><strong>Range</strong><p class=\"mono\">{score['min']} to {score['max']}</p></div>
      <div class=\"card\"><strong>P10 / P25</strong><p class=\"mono\">{score['p10']} / {score['p25']}</p></div>
      <div class=\"card\"><strong>P75 / P90</strong><p class=\"mono\">{score['p75']} / {score['p90']}</p></div>
    </div>

    <h2>Histogram</h2>
    <table>
      <thead><tr><th>Score Bin</th><th>Count</th><th>Percent</th><th>Visual</th></tr></thead>
      <tbody>{''.join(hist_rows)}</tbody>
    </table>

    <h2>Grade Distribution</h2>
    <table>
      <thead><tr><th>Grade</th><th>Count</th><th>Percent</th><th>Visual</th></tr></thead>
      <tbody>{''.join(grade_rows)}</tbody>
    </table>

    <h2>Top Examples</h2>
    <table>
      <thead><tr><th>Rank</th><th>Score</th><th>Grade</th><th>Lineup</th></tr></thead>
      <tbody>{_examples_table(report['topExamples'])}</tbody>
    </table>

    <h2>Bottom Examples</h2>
    <table>
      <thead><tr><th>Rank</th><th>Score</th><th>Grade</th><th>Lineup</th></tr></thead>
      <tbody>{_examples_table(report['bottomExamples'])}</tbody>
    </table>
  </div>
</body>
</html>
"""


def _write_report_bundle(report: dict[str, Any], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    total = report["summary"]["lineups"]

    summary_json = out_dir / "summary.json"
    summary_json.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    score = report["summary"]["score"]
    _write_csv(
        out_dir / "score_summary.csv",
        ["metric", "value"],
        [[k, score[k]] for k in ["mean", "median", "stdev", "min", "p10", "p25", "p75", "p90", "max"]],
    )

    _write_csv(
        out_dir / "grade_distribution.csv",
        ["grade", "count", "percent"],
        [
            [grade, count, f"{_pct(count, total):.2f}"]
            for grade, count in report["summary"]["grades"].items()
        ],
    )

    _write_csv(
        out_dir / "score_histogram.csv",
        ["bucket", "count", "percent"],
        [
            [bucket, count, f"{_pct(count, total):.2f}"]
            for bucket, count in report["summary"]["histogram"].items()
        ],
    )

    markdown_path = out_dir / "report.md"
    markdown_path.write_text(_build_markdown_report(report), encoding="utf-8")

    html_path = out_dir / "report.html"
    html_path.write_text(_build_html_report(report), encoding="utf-8")

    return [
        summary_json,
        out_dir / "score_summary.csv",
        out_dir / "grade_distribution.csv",
        out_dir / "score_histogram.csv",
        markdown_path,
        html_path,
    ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate random NHL lineups and score them using backend.app.game_service.score_lineup."
        )
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10000,
        help="Number of random lineups to score (default: 10000)",
    )
    parser.add_argument(
        "--mode",
        choices=["realistic", "random-any"],
        default="realistic",
        help=(
            "realistic = fills F/F/F/D/D/G from position groups, "
            "random-any = any 6 players in slots"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible simulations",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional output path for full simulation summary JSON",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help=(
            "Optional directory to write visualization bundle "
            "(summary.json, CSV tables, report.md, report.html)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.samples <= 0:
        raise ValueError("--samples must be > 0")

    report = run_simulation(samples=args.samples, mode=args.mode, seed=args.seed)
    _print_report(report)

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with args.json_out.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=True, indent=2)
        print()
        print(f"Wrote JSON summary to {args.json_out}")

    if args.report_dir is not None:
        files = _write_report_bundle(report, args.report_dir)
        print()
        print(f"Wrote report bundle to {args.report_dir}")
        for path in files:
            print(f"  - {path}")


if __name__ == "__main__":
    main()
