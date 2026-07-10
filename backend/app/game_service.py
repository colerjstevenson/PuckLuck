from __future__ import annotations

import json
import logging
import random
import re
import sqlite3
import uuid
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .categories import CategoryDef, build_categories

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
REPO_ROOT = PROJECT_ROOT.parent


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


DATA_DIR_CANDIDATES = _unique_paths([
    PROJECT_ROOT / "data",           # Docker image layout (/app/data)
    REPO_ROOT / "backend" / "data", # Local repo layout (repo/backend/data)
])

RAW_DB_CANDIDATES = [directory / "players_raw.db" for directory in DATA_DIR_CANDIDATES]
COMPACT_JSON_CANDIDATES = [directory / "players_compact.json" for directory in DATA_DIR_CANDIDATES]
RAW_JSON_CANDIDATES = _unique_paths([
    REPO_ROOT / "players.json",
    PROJECT_ROOT / "players.json",
])
EXAMPLE_JSON_CANDIDATES = _unique_paths([
    REPO_ROOT / "data_example.json",
    PROJECT_ROOT / "data_example.json",
])

logger = logging.getLogger(__name__)

NHL_TEAM_ALIASES = [
    "Anaheim Ducks",
    "Mighty Ducks of Anaheim",
    "Arizona Coyotes",
    "Phoenix Coyotes",
    "Utah Hockey Club",
    "Atlanta Flames",
    "Atlanta Thrashers",
    "Boston Bruins",
    "Buffalo Sabres",
    "Calgary Flames",
    "Carolina Hurricanes",
    "Hartford Whalers",
    "Chicago Blackhawks",
    "Chicago Black Hawks",
    "Colorado Avalanche",
    "Colorado Rockies",
    "Columbus Blue Jackets",
    "Dallas Stars",
    "Detroit Red Wings",
    "Detroit Cougars",
    "Detroit Falcons",
    "Edmonton Oilers",
    "Florida Panthers",
    "Los Angeles Kings",
    "Minnesota Wild",
    "Minnesota North Stars",
    "Montreal Canadiens",
    "Montreal Maroons",
    "Nashville Predators",
    "New Jersey Devils",
    "Kansas City Scouts",
    "New York Islanders",
    "New York Rangers",
    "Ottawa Senators",
    "Philadelphia Flyers",
    "Philadelphia Quakers",
    "Pittsburgh Penguins",
    "Pittsburgh Pirates",
    "Quebec Nordiques",
    "San Jose Sharks",
    "Seattle Kraken",
    "St. Louis Blues",
    "St Louis Blues",
    "Tampa Bay Lightning",
    "Toronto Maple Leafs",
    "Toronto Arenas",
    "Toronto St. Patricks",
    "Toronto St Patricks",
    "Vancouver Canucks",
    "Vegas Golden Knights",
    "Washington Capitals",
    "Winnipeg Jets",
    "California Golden Seals",
    "Oakland Seals",
    "Cleveland Barons",
    "New York Americans",
    "Brooklyn Americans",
    "Hamilton Tigers",
]


def _normalize_team_name(team: str) -> str:
    # Normalize accents/punctuation/spacing so minor formatting differences still match NHL aliases.
    text = unicodedata.normalize("NFKD", team)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).strip().upper()
    return re.sub(r"\s+", " ", text)


NHL_TEAM_ALIAS_KEYS: dict[str, str] = {}
for alias in NHL_TEAM_ALIASES:
    key = _normalize_team_name(alias)
    NHL_TEAM_ALIAS_KEYS.setdefault(key, alias)

SLOT_POSITION_GROUP = {
    "F1": "Forward",
    "F2": "Forward",
    "F3": "Forward",
    "D1": "Defense",
    "D2": "Defense",
    "G": "Goalie",
}

SCORE_WEIGHTS = {
    "production": 0.35,
    "trophies": 0.15,
    "cups": 0.10,
    "grit": 0.15,
    "positionFit": 0.15,
    "hallOfFame": 0.10,
}

SCORE_NORMALIZATION = {
    "production": {
        "careerPointsMax": 1600,
        "pointsPerGameMax": 1.8,
        "careerHighPointsMax": 150,
        "playoffPointsMax": 250,
    },
    "trophies": {"awardsMax": 10},
    "cups": {"max": 6},
    "grit": {
        "pimMax": 1500,
        "toiMax": 28,
        "plusMinusRange": (-40, 50),
    },
    "position": {
        "perfect": 1.0,
        "skaterOffPosition": 0.25,
        "goalieOutOfCrease": 0.0,
        "goalieNotInNet": 0.1,
        "vacant": 0.0,
    },
}

GRADE_THRESHOLDS = [
    (97, "A+"),
    (93, "A"),
    (90, "A-"),
    (87, "B+"),
    (83, "B"),
    (80, "B-"),
    (77, "C+"),
    (73, "C"),
    (70, "C-"),
    (67, "D+"),
    (63, "D"),
    (60, "D-"),
    (0, "F"),
]


def _score_to_letter_grade(score: int) -> str:
    for threshold, label in GRADE_THRESHOLDS:
        if score >= threshold:
            return label
    return GRADE_THRESHOLDS[-1][1]


TOTAL_LINEUP_SLOTS = len(SLOT_POSITION_GROUP)


def _parse_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_time_on_ice(value) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        match = re.match(r"^(\d+):(\d{1,2})$", text)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            return round(minutes + seconds / 60.0, 3)
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value is None:
        return low
    return max(low, min(high, value))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _normalize_position_group(raw_position: str, raw_group: str) -> str:
    if raw_group:
        if raw_group.lower().startswith("def"):
            return "Defense"
        if raw_group.lower().startswith("for"):
            return "Forward"
        if raw_group.lower().startswith("goal"):
            return "Goalie"

    pos = (raw_position or "").upper()
    if pos == "G":
        return "Goalie"
    if pos == "D":
        return "Defense"
    return "Forward"


def _clean_nhl_teams(teams: list[str]) -> list[str]:
    if not teams:
        return []
    seen = set()
    cleaned = []
    for team in teams:
        if not team:
            continue
        key = _normalize_team_name(team)
        canonical = NHL_TEAM_ALIAS_KEYS.get(key)
        if not canonical:
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        cleaned.append(canonical)
    return cleaned


def normalize_player(raw: dict) -> dict:
    # Support both raw NHL payloads and already-compacted player rows.
    regular = raw.get("careerStats", {}).get("regularSeason") or raw.get("stats", {})
    position = raw.get("position", "")
    position_group = _normalize_position_group(position, raw.get("positionGroup", ""))
    career_highs = raw.get("careerHighs", {})
    post_season = (
        raw.get("careerStats", {}).get("postSeason")
        or raw.get("postSeason")
        or raw.get("playoffStats")
        or {}
    )

    height_raw = (
        raw.get("height")
        or raw.get("heightInInches")
        or raw.get("heightInches")
    )
    weight_raw = (
        raw.get("weight")
        or raw.get("weightInPounds")
        or raw.get("weightLbs")
    )
    height = _parse_optional_int(height_raw)
    weight = _parse_optional_int(weight_raw)

    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", "Unknown Player"),
        "headshot": raw.get("headshot"),
        "position": position,
        "positionGroup": position_group,
        "birthCountry": raw.get("birthCountry"),
        "birthDate": raw.get("birthDate"),
        "height": height if height is not None else height_raw,
        "weight": weight if weight is not None else weight_raw,
        "teamsPlayedFor": _clean_nhl_teams(raw.get("teamsPlayedFor", [])),
        "rookieSeason": raw.get("rookieSeason"),
        "lastSeason": raw.get("lastSeason"),
        "draftYear": _parse_int(raw.get("draftYear"), 0),
        "draftRound": _parse_int(raw.get("draftRound"), 0),
        "draftPick": _parse_int(raw.get("draftPick"), 0),
        "active": bool(raw.get("active", False)),
        "sweaterNumber": _parse_int(raw.get("sweaterNumber"), 0) if raw.get("sweaterNumber") not in (None, "") else None,
        "awards": raw.get("awards", []),
        "inHHOF": bool(raw.get("inHHOF", False)),
        "cups": _parse_int(raw.get("cups"), 0),
        "stats": {
            "gamesPlayed": _parse_int(regular.get("gamesPlayed"), 0),
            "goals": _parse_int(regular.get("goals"), 0),
            "assists": _parse_int(regular.get("assists"), 0),
            "points": _parse_int(regular.get("points"), 0),
            "pim": _parse_int(regular.get("pim"), 0),
            "wins": _parse_int(regular.get("wins"), 0),
            "savePctg": _parse_float(regular.get("savePctg"), 0.0),
            "shots": _parse_int(regular.get("shots"), 0),
            "plusMinus": _parse_int(regular.get("plusMinus"), 0),
            "toi": _parse_time_on_ice(
                regular.get("toi")
                or regular.get("timeOnIce")
                or regular.get("averageTimeOnIce")
                or regular.get("avgToi")
                or regular.get("avgTimeOnIce")
            ),
            "playoffPoints": _parse_int(post_season.get("points"), 0),
            "playoffGames": _parse_int(post_season.get("gamesPlayed"), 0),
        },
        "careerHighs": {
            "goals": _parse_int(career_highs.get("goals"), 0),
            "points": _parse_int(career_highs.get("points"), 0),
            "pim": _parse_int(career_highs.get("pim"), 0),
        },
    }


def _read_players_from_sqlite() -> list[dict] | None:
    for db_path in RAW_DB_CANDIDATES:
        if not db_path.exists():
            continue

        try:
            with sqlite3.connect(db_path) as conn:
                rows = conn.execute("SELECT compact_json FROM players_raw").fetchall()
        except sqlite3.Error as exc:
            logger.warning("SQLite load failed for %s: %s", db_path, exc)
            continue

        players: list[dict] = []
        for row in rows:
            compact_json = row[0]
            if not compact_json:
                continue
            try:
                payload = json.loads(compact_json)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                players.append(payload)

        if players:
            return players

        logger.warning("SQLite source %s yielded 0 valid player rows. Trying JSON fallback.", db_path)

    return None


def _read_players_from_json(path: Path) -> list[dict] | None:
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.warning("JSON load failed for %s: %s", path, exc)
        return None

    if isinstance(data, dict):
        data = [data]

    return [item for item in data if isinstance(item, dict)]


def _load_players_bundle() -> dict:
    # Prefer canonical SQLite output and only fall back to JSON during transition windows.
    sqlite_rows = _read_players_from_sqlite()
    if sqlite_rows is not None:
        normalized = [normalize_player(item) for item in sqlite_rows]
        players = [p for p in normalized if p.get("id")]
        if players:
            return {
                "players": players,
                "dataSource": "sqlite",
                "sourcePath": "|".join(str(path) for path in RAW_DB_CANDIDATES),
                "sourceRowCount": len(sqlite_rows),
                "ready": True,
            }

    for source, source_name in [
        *[(path, "compact-json") for path in COMPACT_JSON_CANDIDATES],
        *[(path, "raw-json") for path in RAW_JSON_CANDIDATES],
        *[(path, "example-json") for path in EXAMPLE_JSON_CANDIDATES],
    ]:
        data = _read_players_from_json(source)
        if data is None:
            continue
        normalized = [normalize_player(item) for item in data]
        players = [p for p in normalized if p.get("id")]
        if players:
            return {
                "players": players,
                "dataSource": source_name,
                "sourcePath": str(source),
                "sourceRowCount": len(data),
                "ready": True,
            }
        logger.warning("%s source %s yielded 0 valid players. Trying next source.", source_name, source)

    return {
        "players": [],
        "dataSource": "missing",
        "sourcePath": "",
        "sourceRowCount": 0,
        "ready": False,
    }


@lru_cache(maxsize=1)
def load_players() -> list[dict]:
    return _load_players_bundle()["players"]


@lru_cache(maxsize=1)
def _load_data_state() -> dict:
    return _load_players_bundle()


def data_ready() -> bool:
    return bool(_load_data_state().get("ready"))


@lru_cache(maxsize=1)
def load_categories() -> dict[str, CategoryDef]:
    categories = build_categories()
    return {c.id: c for c in categories}


def _eligible_players(left_category_id: str, right_category_id: str, players: list[dict] | None = None) -> list[dict]:
    players = players or load_players()
    categories = load_categories()
    left = categories.get(left_category_id)
    right = categories.get(right_category_id)
    if not left or not right:
        return []
    return [p for p in players if left.predicate(p) and right.predicate(p)]


def list_categories() -> list[dict]:
    return [
        {"id": c.id, "label": c.label, "group": c.group, "weight": c.weight}
        for c in load_categories().values()
    ]


def spin(keep_side: str | None = None, keep_category_id: str | None = None) -> dict:
    players = load_players()
    all_categories = list(load_categories().values())

    # Weighted picks keep common categories lively while still surfacing niche constraints.
    weighted = [c for c in all_categories for _ in range(max(c.weight, 1))]
    kept = None
    if keep_side and keep_category_id:
        kept = load_categories().get(keep_category_id)

    for _ in range(300):
        left = kept if keep_side == "left" and kept else random.choice(weighted)
        right = kept if keep_side == "right" and kept else random.choice(weighted)
        if left.id == right.id:
            continue
        if left.group == right.group:
            continue

        eligible = _eligible_players(left.id, right.id, players)
        if eligible:
            return {
                "left": {"id": left.id, "label": left.label, "group": left.group},
                "right": {"id": right.id, "label": right.label, "group": right.group},
                "roundToken": str(uuid.uuid4()),
                "eligibleCount": len(eligible),
            }

    return {
        "left": {"id": all_categories[0].id, "label": all_categories[0].label, "group": all_categories[0].group},
        "right": {"id": all_categories[1].id, "label": all_categories[1].label, "group": all_categories[1].group},
        "roundToken": str(uuid.uuid4()),
        "eligibleCount": 0,
    }


def eligible(left_category_id: str, right_category_id: str, limit: int = 120) -> tuple[int, list[dict]]:
    all_matches = _eligible_players(left_category_id, right_category_id)
    return len(all_matches), all_matches[:limit]


def get_player(player_id: str) -> dict | None:
    for player in load_players():
        if player.get("id") == player_id:
            return player
    return None


def score_lineup(lineup: list[dict]) -> dict:
    players_by_id = {p["id"]: p for p in load_players()}
    penalties = []
    warnings = []

    used_slots = set()
    picked_players = []
    slot_map: dict[str, dict] = {}

    for pick in lineup:
        slot = pick.get("slot")
        player_id = pick.get("playerId")
        if slot in used_slots:
            warnings.append(f"Slot {slot} was used multiple times.")
            continue
        used_slots.add(slot)

        player = players_by_id.get(player_id)
        if not player:
            warnings.append(f"Unknown player id: {player_id}")
            continue

        picked_players.append(player)
        slot_map[slot] = player

    production_scores: list[float] = []
    trophy_scores: list[float] = []
    cup_scores: list[float] = []
    grit_scores: list[float] = []
    hall_scores: list[float] = []

    production_norm = SCORE_NORMALIZATION["production"]
    trophy_norm = SCORE_NORMALIZATION["trophies"]
    cup_norm = SCORE_NORMALIZATION["cups"]
    grit_norm = SCORE_NORMALIZATION["grit"]

    for player in picked_players:
        stats = player.get("stats") or {}
        career_points = _parse_int(stats.get("points"), 0)
        games_played = _parse_int(stats.get("gamesPlayed"), 0)

        ppg_raw = stats.get("pointsPerGame")
        if ppg_raw in (None, ""):
            points_per_game = career_points / games_played if games_played else 0.0
        else:
            points_per_game = _parse_float(ppg_raw, 0.0)
            if points_per_game == 0.0 and games_played:
                points_per_game = career_points / games_played

        career_high_points = _parse_int((player.get("careerHighs") or {}).get("points"), 0)
        playoff_points = _parse_int(stats.get("playoffPoints"), 0)

        prod_norms = [
            _clamp(career_points / production_norm["careerPointsMax"]) if production_norm["careerPointsMax"] else 0.0,
            _clamp(points_per_game / production_norm["pointsPerGameMax"]) if production_norm["pointsPerGameMax"] else 0.0,
            _clamp(career_high_points / production_norm["careerHighPointsMax"]) if production_norm["careerHighPointsMax"] else 0.0,
            _clamp(playoff_points / production_norm["playoffPointsMax"]) if production_norm["playoffPointsMax"] else 0.0,
        ]
        production_scores.append(_mean(prod_norms))

        awards_count = len(player.get("awards") or [])
        trophy_scores.append(
            _clamp(awards_count / trophy_norm["awardsMax"]) if trophy_norm["awardsMax"] else 0.0
        )

        cup_total = _parse_int(player.get("cups"), 0)
        cup_scores.append(
            _clamp(cup_total / cup_norm["max"]) if cup_norm["max"] else 0.0
        )

        pim = _parse_int(stats.get("pim"), 0)
        toi_value = stats.get("toi")
        if isinstance(toi_value, str):
            toi_value = _parse_time_on_ice(toi_value)
        if toi_value is None:
            toi_value = 0.0
        else:
            try:
                toi_value = float(toi_value)
            except (TypeError, ValueError):
                toi_value = 0.0

        plus_minus_raw = stats.get("plusMinus")
        plus_minus = _parse_int(plus_minus_raw, 0)

        pm_low, pm_high = grit_norm["plusMinusRange"]
        if pm_high == pm_low:
            plus_minus_norm = 0.0
        else:
            plus_minus_norm = _clamp((plus_minus - pm_low) / (pm_high - pm_low))

        grit_components = [
            _clamp(pim / grit_norm["pimMax"]) if grit_norm["pimMax"] else 0.0,
            _clamp(toi_value / grit_norm["toiMax"]) if grit_norm["toiMax"] else 0.0,
            plus_minus_norm,
        ]
        grit_scores.append(_mean(grit_components))

        hall_scores.append(1.0 if player.get("inHHOF") else 0.0)

    position_norm = SCORE_NORMALIZATION["position"]
    position_scores: list[float] = []
    lineup_incomplete = False

    for slot, expected_group in SLOT_POSITION_GROUP.items():
        player = slot_map.get(slot)
        if not player:
            position_scores.append(position_norm["vacant"])
            lineup_incomplete = True
            continue

        actual_group = player.get("positionGroup")
        player_name = player.get("name", "Unknown Player")

        if actual_group == expected_group:
            position_scores.append(position_norm["perfect"])
        elif actual_group == "Goalie" and expected_group != "Goalie":
            position_scores.append(position_norm["goalieOutOfCrease"])
            penalties.append(f"{player_name} is a goalie outside the crease ({slot}).")
        elif expected_group == "Goalie" and actual_group != "Goalie":
            position_scores.append(position_norm["goalieNotInNet"])
            penalties.append(f"{player_name} is not a goalie but was placed in G.")
        else:
            position_scores.append(position_norm["skaterOffPosition"])
            penalties.append(f"{player_name} is off-position in {slot}.")

    component_values = {
        "production": _mean(production_scores),
        "trophies": _mean(trophy_scores),
        "cups": _mean(cup_scores),
        "grit": _mean(grit_scores),
        "positionFit": _mean(position_scores),
        "hallOfFame": _mean(hall_scores),
    }

    weighted = {
        name: component_values[name] * SCORE_WEIGHTS[name]
        for name in SCORE_WEIGHTS
    }
    weighted_total = sum(weighted.values())
    lineup_completion = len(slot_map) / TOTAL_LINEUP_SLOTS if TOTAL_LINEUP_SLOTS else 0.0

    if lineup_completion < 1.0 or lineup_incomplete:
        warning_msg = "Lineup incomplete. Fill all six slots for completion bonus."
        if warning_msg not in warnings:
            warnings.append(warning_msg)

    total_score = max(round(weighted_total * lineup_completion * 100), 0)
    grade = _score_to_letter_grade(total_score)

    breakdown = {
        name: {
            "value": component_values[name],
            "weight": SCORE_WEIGHTS[name],
            "weighted": weighted[name],
        }
        for name in SCORE_WEIGHTS
    }
    breakdown["lineupCompletion"] = lineup_completion
    breakdown["totalWeighted"] = weighted_total

    return {
        "totalScore": total_score,
        "grade": grade,
        "breakdown": breakdown,
        "penalties": penalties,
        "warnings": warnings,
    }


def metadata() -> dict:
    grouped = defaultdict(int)
    for c in load_categories().values():
        grouped[c.group] += 1
    state = _load_data_state()
    return {
        "playerCount": len(load_players()),
        "categoryCount": len(load_categories()),
        "categoryGroups": dict(grouped),
        "dataSource": state.get("dataSource", "unknown"),
        "sourceRowCount": int(state.get("sourceRowCount", 0) or 0),
        "dataReady": bool(state.get("ready")),
    }
