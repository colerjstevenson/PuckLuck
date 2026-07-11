from __future__ import annotations

import argparse
import json
import random
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from simulate_scoring import GRADE_ORDER, run_simulation

import app.game_service as game_service  # type: ignore[import-not-found]

WEIGHT_KEYS = [
    "production",
    "trophies",
    "cups",
    "grit",
    "positionFit",
    "hallOfFame",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run scoring simulations across multiple SCORE_WEIGHTS sets and rank which "
            "configuration best matches a target score distribution."
        )
    )
    parser.add_argument(
        "--target-json",
        type=Path,
        required=True,
        help=(
            "Target distribution JSON. Can be a full simulate_scoring summary report "
            "(contains summary.histogram/summary.grades) or an object with histogram/grades."
        ),
    )
    parser.add_argument(
        "--weight-sets-json",
        type=Path,
        default=None,
        help=(
            "Optional candidate weight sets. Supports either: "
            "(1) object of name -> weights, or "
            "(2) list of objects with {name, weights}."
        ),
    )
    parser.add_argument(
        "--auto-sets",
        type=int,
        default=50,
        help=(
            "Number of random auto-generated candidate sets to add (default: 50)."
        ),
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=6000,
        help="Simulated lineups per candidate (default: 6000).",
    )
    parser.add_argument(
        "--mode",
        choices=["realistic", "random-any"],
        default="realistic",
        help="Simulation lineup mode (default: realistic).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help=(
            "Base random seed. The same deterministic sequence is used per candidate "
            "for fair comparison (default: 42)."
        ),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="How many top-ranked candidates to print (default: 10).",
    )
    parser.add_argument(
        "--hist-weight",
        type=float,
        default=0.5,
        help="Composite loss weight for histogram fit (default: 0.5).",
    )
    parser.add_argument(
        "--grade-weight",
        type=float,
        default=0.3,
        help="Composite loss weight for grade fit (default: 0.3).",
    )
    parser.add_argument(
        "--stats-weight",
        type=float,
        default=0.2,
        help="Composite loss weight for score-stat fit (default: 0.2).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write full ranking output JSON.",
    )
    return parser.parse_args()


def _normalize_weight_set(raw: dict[str, Any], base: dict[str, float]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for key in WEIGHT_KEYS:
        value = raw[key] if key in raw else base[key]
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Weight {key} is not numeric: {value}") from exc
        if number < 0:
            raise ValueError(f"Weight {key} must be >= 0 (got {number})")
        merged[key] = number

    total = sum(merged.values())
    if total <= 0:
        raise ValueError("Weight set total must be > 0")

    return {k: merged[k] / total for k in WEIGHT_KEYS}


def _load_weight_sets(path: Path, base: dict[str, float]) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        for name, weights in payload.items():
            if not isinstance(weights, dict):
                raise ValueError(f"Weight set {name!r} must be an object of weights")
            candidates.append({"name": str(name), "weights": _normalize_weight_set(weights, base)})
        return candidates

    if not isinstance(payload, list):
        raise ValueError("weight-sets-json must be an object or a list")

    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError("Each list item in weight-sets-json must be an object")

        name = str(item.get("name", f"set_{idx + 1}"))
        weights_raw = item.get("weights", item)
        if not isinstance(weights_raw, dict):
            raise ValueError(f"Weight set {name!r} must define a weights object")
        candidates.append({"name": name, "weights": _normalize_weight_set(weights_raw, base)})

    return candidates


def _random_weight_sets(count: int, seed: int, base: dict[str, float]) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    generated: list[dict[str, Any]] = []

    for idx in range(count):
        alpha = 3.0
        raw_values = {
            key: rng.gammavariate(alpha * max(base[key], 0.001), 1.0)
            for key in WEIGHT_KEYS
        }
        weights = _normalize_weight_set(raw_values, base)
        generated.append({"name": f"auto_{idx + 1:03d}", "weights": weights})

    return generated


def _extract_target(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else payload
    if not isinstance(summary, dict):
        raise ValueError("target JSON must be an object")

    histogram = summary.get("histogram")
    grades = summary.get("grades")
    score = summary.get("score")

    if not isinstance(histogram, dict) or not histogram:
        raise ValueError("target JSON must include histogram")
    if not isinstance(grades, dict) or not grades:
        raise ValueError("target JSON must include grades")
    if not isinstance(score, dict):
        score = {}

    return {
        "histogram": {str(k): float(v) for k, v in histogram.items()},
        "grades": {str(k): float(v) for k, v in grades.items()},
        "score": {
            k: float(v)
            for k, v in score.items()
            if k in {"mean", "median", "stdev"}
        },
    }


def _to_distribution(raw: dict[str, float], ordered_keys: list[str]) -> list[float]:
    total = sum(max(0.0, float(v)) for v in raw.values())
    if total <= 0:
        return [0.0 for _ in ordered_keys]
    return [max(0.0, float(raw.get(key, 0.0))) / total for key in ordered_keys]


def _rmse(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a:
        return 0.0
    mse = sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)) / len(vec_a)
    return mse ** 0.5


def _score_stats_error(target_score: dict[str, float], candidate_score: dict[str, Any]) -> float:
    scales = {
        "mean": 100.0,
        "median": 100.0,
        "stdev": 50.0,
    }
    keys = [k for k in ("mean", "median", "stdev") if k in target_score and k in candidate_score]
    if not keys:
        return 0.0

    total = 0.0
    for key in keys:
        scale = scales[key]
        total += abs(float(candidate_score[key]) - float(target_score[key])) / scale
    return total / len(keys)


def _fit_loss(
    target: dict[str, Any],
    candidate_summary: dict[str, Any],
    hist_weight: float,
    grade_weight: float,
    stats_weight: float,
) -> dict[str, float]:
    hist_keys = sorted(set(target["histogram"].keys()) | set(candidate_summary["histogram"].keys()))
    target_hist = _to_distribution(target["histogram"], hist_keys)
    candidate_hist = _to_distribution(candidate_summary["histogram"], hist_keys)
    histogram_rmse = _rmse(target_hist, candidate_hist)

    grade_keys = [g for g in GRADE_ORDER if g in target["grades"] or g in candidate_summary["grades"]]
    target_grades = _to_distribution(target["grades"], grade_keys)
    candidate_grades = _to_distribution(candidate_summary["grades"], grade_keys)
    grades_rmse = _rmse(target_grades, candidate_grades)

    stats_err = _score_stats_error(target["score"], candidate_summary["score"])

    composite = (
        (hist_weight * histogram_rmse)
        + (grade_weight * grades_rmse)
        + (stats_weight * stats_err)
    )

    return {
        "composite": composite,
        "histogramRmse": histogram_rmse,
        "gradesRmse": grades_rmse,
        "statsError": stats_err,
    }


@contextmanager
def _temporary_weights(weights: dict[str, float]):
    original = dict(game_service.SCORE_WEIGHTS)
    try:
        game_service.SCORE_WEIGHTS.clear()
        game_service.SCORE_WEIGHTS.update(weights)
        yield
    finally:
        game_service.SCORE_WEIGHTS.clear()
        game_service.SCORE_WEIGHTS.update(original)


def _print_rankings(results: list[dict[str, Any]], top_k: int) -> None:
    print("== Weight Set Fit Ranking ==")
    print(
        "rank  name         loss      hist_rmse  grades_rmse stats_err  "
        "mean   stdev"
    )

    for rank, item in enumerate(results[:top_k], start=1):
        summary = item["summary"]["score"]
        fit = item["fit"]
        print(
            f"{rank:>4}  {item['name'][:12]:<12} "
            f"{fit['composite']:.6f} "
            f"{fit['histogramRmse']:.6f} "
            f"{fit['gradesRmse']:.6f} "
            f"{fit['statsError']:.6f} "
            f"{summary['mean']:>6} {summary['stdev']:>6}"
        )


def main() -> None:
    args = _parse_args()

    if args.samples <= 0:
        raise ValueError("--samples must be > 0")
    if args.auto_sets < 0:
        raise ValueError("--auto-sets must be >= 0")

    coeff_sum = args.hist_weight + args.grade_weight + args.stats_weight
    if coeff_sum <= 0:
        raise ValueError("hist/grade/stats weights must sum to > 0")

    hist_w = args.hist_weight / coeff_sum
    grade_w = args.grade_weight / coeff_sum
    stats_w = args.stats_weight / coeff_sum

    target_payload = json.loads(args.target_json.read_text(encoding="utf-8"))
    target = _extract_target(target_payload)

    base_weights = {k: float(game_service.SCORE_WEIGHTS[k]) for k in WEIGHT_KEYS}
    candidates: list[dict[str, Any]] = [{"name": "baseline", "weights": dict(base_weights)}]

    if args.weight_sets_json is not None:
        candidates.extend(_load_weight_sets(args.weight_sets_json, base_weights))

    if args.auto_sets > 0:
        candidates.extend(_random_weight_sets(args.auto_sets, args.seed, base_weights))

    deduped: list[dict[str, Any]] = []
    seen_signatures: set[tuple[float, ...]] = set()
    for item in candidates:
        signature = tuple(round(item["weights"][key], 8) for key in WEIGHT_KEYS)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        deduped.append(item)

    results: list[dict[str, Any]] = []
    for idx, candidate in enumerate(deduped):
        sim_seed = args.seed + idx
        with _temporary_weights(candidate["weights"]):
            report = run_simulation(samples=args.samples, mode=args.mode, seed=sim_seed)

        fit = _fit_loss(target, report["summary"], hist_w, grade_w, stats_w)
        results.append(
            {
                "name": candidate["name"],
                "weights": candidate["weights"],
                "fit": fit,
                "settings": {
                    "samples": args.samples,
                    "mode": args.mode,
                    "seed": sim_seed,
                },
                "summary": report["summary"],
            }
        )

    results.sort(key=lambda item: item["fit"]["composite"])

    _print_rankings(results, args.top_k)

    best = results[0]
    print()
    print("Best configuration")
    print(f"  name: {best['name']}")
    print(f"  loss: {best['fit']['composite']:.6f}")
    print("  weights:")
    for key in WEIGHT_KEYS:
        print(f"    {key}: {best['weights'][key]:.6f}")

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        bundle = {
            "targetJson": str(args.target_json),
            "samples": args.samples,
            "mode": args.mode,
            "baseSeed": args.seed,
            "lossWeights": {
                "histogram": hist_w,
                "grades": grade_w,
                "stats": stats_w,
            },
            "candidateCount": len(results),
            "best": best,
            "ranked": results,
        }
        args.json_out.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")
        print()
        print(f"Wrote ranking output to {args.json_out}")


if __name__ == "__main__":
    main()
