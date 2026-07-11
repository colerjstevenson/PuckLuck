from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.game_service import GRADE_RANK, metadata, score_lineup, load_players  # type: ignore[import-not-found]  # noqa: E402

SLOT_ORDER = ["F1", "F2", "F3", "D1", "D2", "G"]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search lineups built from real player data and prove A+ and A++ are achievable. "
            "Exits with code 1 if either grade is not found."
        )
    )
    parser.add_argument(
        "--random-samples",
        type=int,
        default=25000,
        help="How many random realistic lineups to sample first (default: 25000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42).",
    )
    parser.add_argument(
        "--top-forwards",
        type=int,
        default=16,
        help="Top heuristic forwards to include in exhaustive phase (default: 16).",
    )
    parser.add_argument(
        "--top-defense",
        type=int,
        default=12,
        help="Top heuristic defensemen to include in exhaustive phase (default: 12).",
    )
    parser.add_argument(
        "--top-goalies",
        type=int,
        default=8,
        help="Top heuristic goalies to include in exhaustive phase (default: 8).",
    )
    parser.add_argument(
        "--min-games",
        type=int,
        default=200,
        help="Exclude players with fewer than this many regular-season games (default: 200).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write a machine-readable proof report.",
    )
    return parser.parse_args()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _player_quality_heuristic(player: dict[str, Any]) -> float:
    stats = player.get("stats") or {}
    group = player.get("positionGroup")

    games = _as_int(stats.get("gamesPlayed"), 0)
    points = _as_int(stats.get("points"), 0)
    playoff_points = _as_int(stats.get("playoffPoints"), 0)
    ppg = (points / games) if games > 0 else 0.0

    awards = len(player.get("awards") or [])
    cups = _as_int(player.get("cups"), 0)
    hall = 1.0 if player.get("inHHOF") else 0.0

    if group == "Goalie":
        wins = _as_int(stats.get("wins"), 0)
        save_pctg = _as_float(stats.get("savePctg"), 0.0)
        goalie_signal = (
            0.4 * _clamp(wins / 700)
            + 0.4 * _clamp((save_pctg - 0.86) / 0.07)
            + 0.2 * _clamp(games / 1500)
        )
        return (
            0.65 * goalie_signal
            + 0.15 * _clamp(awards / 10)
            + 0.1 * _clamp(cups / 6)
            + 0.1 * hall
        )

    career_high_points = _as_int((player.get("careerHighs") or {}).get("points"), 0)
    plus_minus = _as_int(stats.get("plusMinus"), 0)
    pim = _as_int(stats.get("pim"), 0)
    toi = _as_float(stats.get("toi"), 0.0)

    production = (
        0.35 * _clamp(points / 1600)
        + 0.3 * _clamp(ppg / 1.8)
        + 0.2 * _clamp(career_high_points / 150)
        + 0.15 * _clamp(playoff_points / 250)
    )
    grit = (
        0.35 * _clamp(pim / 1500)
        + 0.35 * _clamp(toi / 28)
        + 0.3 * _clamp((plus_minus + 40) / 90)
    )

    return (
        0.5 * production
        + 0.16 * _clamp(awards / 10)
        + 0.12 * _clamp(cups / 6)
        + 0.12 * grit
        + 0.1 * hall
    )


def _build_lineup(forwards: list[dict[str, Any]], defense: list[dict[str, Any]], goalie: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"slot": "F1", "playerId": forwards[0]["id"]},
        {"slot": "F2", "playerId": forwards[1]["id"]},
        {"slot": "F3", "playerId": forwards[2]["id"]},
        {"slot": "D1", "playerId": defense[0]["id"]},
        {"slot": "D2", "playerId": defense[1]["id"]},
        {"slot": "G", "playerId": goalie["id"]},
    ]


def _lineup_to_named_map(lineup: list[dict[str, str]], by_id: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    mapped: dict[str, dict[str, str]] = {}
    for pick in lineup:
        slot = pick["slot"]
        player = by_id.get(pick["playerId"], {})
        mapped[slot] = {
            "id": pick["playerId"],
            "name": str(player.get("name", pick["playerId"])),
            "positionGroup": str(player.get("positionGroup", "Unknown")),
        }
    return mapped


def _grade_at_least(actual: str, target: str) -> bool:
    return GRADE_RANK.get(actual, -1) >= GRADE_RANK.get(target, -1)


def _capture_proof(
    target_grade: str,
    lineup: list[dict[str, str]],
    score: dict[str, Any],
    players_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "targetGrade": target_grade,
        "actualGrade": score["grade"],
        "totalScore": score["totalScore"],
        "finalScoreEquation": score.get("finalScoreEquation"),
        "goalieQuality": score.get("goalieQuality"),
        "lineup": _lineup_to_named_map(lineup, players_by_id),
        "breakdown": score.get("breakdown"),
        "weightedContribution": score.get("weightedContribution"),
        "penalties": score.get("penalties", []),
        "warnings": score.get("warnings", []),
    }


def main() -> None:
    args = _parse_args()
    rng = random.Random(args.seed)

    players = load_players()
    if not players:
        raise RuntimeError("No players loaded. Build data first (backend/data artifacts).")

    players_by_id = {player["id"]: player for player in players if player.get("id")}
    eligible_players = [
        player
        for player in players
        if _as_int((player.get("stats") or {}).get("gamesPlayed"), 0) >= max(args.min_games, 0)
    ]

    forwards = [p for p in eligible_players if p.get("positionGroup") == "Forward"]
    defense = [p for p in eligible_players if p.get("positionGroup") == "Defense"]
    goalies = [p for p in eligible_players if p.get("positionGroup") == "Goalie"]

    if len(forwards) < 3 or len(defense) < 2 or len(goalies) < 1:
        raise RuntimeError("Insufficient players by group to build a valid lineup.")

    proofs: dict[str, dict[str, Any] | None] = {"A+": None, "A++": None}
    best_seen: dict[str, Any] = {"score": -1, "grade": "F", "lineup": None, "result": None}
    evaluated = 0

    def evaluate_lineup(lineup: list[dict[str, str]]) -> None:
        nonlocal evaluated, best_seen
        result = score_lineup(lineup)
        evaluated += 1

        if int(result["totalScore"]) > int(best_seen["score"]):
            best_seen = {
                "score": int(result["totalScore"]),
                "grade": str(result["grade"]),
                "lineup": lineup,
                "result": result,
            }

        for target in ("A+", "A++"):
            if proofs[target] is not None:
                continue
            if _grade_at_least(str(result["grade"]), target):
                proofs[target] = _capture_proof(target, lineup, result, players_by_id)

    # Phase 1: random realistic sampling for fast discovery.
    for _ in range(max(args.random_samples, 0)):
        lineup = _build_lineup(
            forwards=rng.sample(forwards, 3),
            defense=rng.sample(defense, 2),
            goalie=rng.choice(goalies),
        )
        evaluate_lineup(lineup)
        if proofs["A+"] and proofs["A++"]:
            break

    # Phase 2: targeted exhaustive search over top heuristic candidates.
    if proofs["A+"] is None or proofs["A++"] is None:
        ranked_forwards = sorted(forwards, key=_player_quality_heuristic, reverse=True)[: max(args.top_forwards, 3)]
        ranked_defense = sorted(defense, key=_player_quality_heuristic, reverse=True)[: max(args.top_defense, 2)]
        ranked_goalies = sorted(goalies, key=_player_quality_heuristic, reverse=True)[: max(args.top_goalies, 1)]

        for f_line in itertools.combinations(ranked_forwards, 3):
            for d_pair in itertools.combinations(ranked_defense, 2):
                for goalie in ranked_goalies:
                    lineup = _build_lineup(list(f_line), list(d_pair), goalie)
                    evaluate_lineup(lineup)
                    if proofs["A+"] and proofs["A++"]:
                        break
                if proofs["A+"] and proofs["A++"]:
                    break
            if proofs["A+"] and proofs["A++"]:
                break

    report = {
        "settings": {
            "seed": args.seed,
            "randomSamples": args.random_samples,
            "topForwards": args.top_forwards,
            "topDefense": args.top_defense,
            "topGoalies": args.top_goalies,
            "minGames": args.min_games,
        },
        "data": {
            "metadata": metadata(),
            "poolSizes": {
                "total": len(players),
                "eligibleTotal": len(eligible_players),
                "forward": len(forwards),
                "defense": len(defense),
                "goalie": len(goalies),
            },
        },
        "evaluatedLineups": evaluated,
        "proofs": proofs,
        "bestSeen": {
            "totalScore": best_seen["score"],
            "grade": best_seen["grade"],
            "lineup": _lineup_to_named_map(best_seen["lineup"], players_by_id) if best_seen["lineup"] else None,
            "breakdown": (best_seen["result"] or {}).get("breakdown") if best_seen["result"] else None,
            "weightedContribution": (best_seen["result"] or {}).get("weightedContribution") if best_seen["result"] else None,
        },
        "success": bool(proofs["A+"] and proofs["A++"]),
    }

    print("== Elite Grade Proof Search ==")
    print(f"Evaluated lineups: {evaluated}")
    print(f"Min games filter: {args.min_games}")
    print(f"Best seen: {best_seen['score']} ({best_seen['grade']})")
    print(f"A+ found: {'yes' if proofs['A+'] else 'no'}")
    print(f"A++ found: {'yes' if proofs['A++'] else 'no'}")

    for grade in ("A+", "A++"):
        proof = proofs[grade]
        if not proof:
            continue
        print()
        print(f"-- Proof for {grade} --")
        print(
            f"score={proof['totalScore']} grade={proof['actualGrade']} "
            f"goalieQuality={proof.get('goalieQuality')}"
        )
        for slot in SLOT_ORDER:
            player = proof["lineup"][slot]
            print(f"{slot}: {player['name']} ({player['id']}) [{player['positionGroup']}]")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved JSON report: {args.json_out}")

    if report["success"]:
        return

    missing = [grade for grade in ("A+", "A++") if proofs[grade] is None]
    raise SystemExit(f"Failed to prove grades with current search budget. Missing: {', '.join(missing)}")


if __name__ == "__main__":
    main()