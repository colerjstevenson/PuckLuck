from __future__ import annotations

import json
import random
import re
import uuid
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .categories import CategoryDef, build_categories

ROOT = Path(__file__).resolve().parents[2]
COMPACT_DATA_PATH = ROOT / "backend" / "data" / "players_compact.json"
RAW_DATA_PATH = ROOT / "players.json"
EXAMPLE_DATA_PATH = ROOT / "data_example.json"

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

    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", "Unknown Player"),
        "headshot": raw.get("headshot"),
        "position": position,
        "positionGroup": position_group,
        "birthCountry": raw.get("birthCountry"),
        "birthDate": raw.get("birthDate"),
        "height": raw.get("height"),
        "weight": _parse_optional_int(raw.get("weight")),
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
            "toi": _parse_time_on_ice(regular.get("toi") or regular.get("timeOnIce") or regular.get("averageTimeOnIce")),
        },
        "careerHighs": {
            "goals": _parse_int(career_highs.get("goals"), 0),
            "points": _parse_int(career_highs.get("points"), 0),
            "pim": _parse_int(career_highs.get("pim"), 0),
        },
    }


@lru_cache(maxsize=1)
def load_players() -> list[dict]:
    source = None
    if COMPACT_DATA_PATH.exists():
        source = COMPACT_DATA_PATH
    elif RAW_DATA_PATH.exists():
        source = RAW_DATA_PATH
    elif EXAMPLE_DATA_PATH.exists():
        source = EXAMPLE_DATA_PATH

    if source is None:
        return []

    with source.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    normalized = [normalize_player(item) for item in data if isinstance(item, dict)]
    return [p for p in normalized if p.get("id")]


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
    slot_map = {}

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

    production = 0
    awards = 0

    for player in picked_players:
        stats = player.get("stats", {})
        production += int(stats.get("points", 0) * 0.6 + stats.get("goals", 0) * 0.25 + stats.get("assists", 0) * 0.15)
        awards += len(player.get("awards", [])) * 8
        awards += int(player.get("cups", 0)) * 12
        if player.get("inHHOF"):
            awards += 25

    countries = {p.get("birthCountry") for p in picked_players if p.get("birthCountry")}
    groups = {p.get("positionGroup") for p in picked_players if p.get("positionGroup")}
    diversity = len(countries) * 6 + len(groups) * 5

    position_fit = 0
    for slot, player in slot_map.items():
        expected = SLOT_POSITION_GROUP.get(slot)
        actual = player.get("positionGroup")
        if expected == actual:
            position_fit += 10
            continue

        if actual == "Goalie" and expected != "Goalie":
            position_fit -= 35
            penalties.append(f"{player['name']} is a goalie outside the crease ({slot}).")
        elif expected == "Goalie" and actual != "Goalie":
            position_fit -= 30
            penalties.append(f"{player['name']} is not a goalie but was placed in G.")
        else:
            position_fit -= 15
            penalties.append(f"{player['name']} is off-position in {slot}.")

    completion_bonus = 50 if len(slot_map) == 6 else 0
    if completion_bonus == 0:
        warnings.append("Lineup incomplete. Fill all six slots for completion bonus.")

    total = production + awards + diversity + position_fit + completion_bonus

    return {
        "totalScore": max(total, 0),
        "breakdown": {
            "production": production,
            "awards": awards,
            "diversity": diversity,
            "positionFit": position_fit,
            "completionBonus": completion_bonus,
        },
        "penalties": penalties,
        "warnings": warnings,
    }


def metadata() -> dict:
    grouped = defaultdict(int)
    for c in load_categories().values():
        grouped[c.group] += 1
    return {
        "playerCount": len(load_players()),
        "categoryCount": len(load_categories()),
        "categoryGroups": dict(grouped),
    }
