from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Updated path to locate players.json in the nhl-api-explorer data directory
INPUT_PATH = ROOT / "nhl-api-explorer" / "public" / "data" / "players.json"
OUTPUT_PATH = ROOT / "backend" / "data" / "players_compact.json"


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


def _normalize_position_group(position: str, position_group: str) -> str:
    if position_group:
        text = position_group.lower()
        if text.startswith("for"):
            return "Forward"
        if text.startswith("def"):
            return "Defense"
        if text.startswith("goal"):
            return "Goalie"
    if (position or "").upper() == "G":
        return "Goalie"
    if (position or "").upper() == "D":
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
    regular = raw.get("careerStats", {}).get("regularSeason", {})

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
        "position": raw.get("position", ""),
        "positionGroup": _normalize_position_group(raw.get("position", ""), raw.get("positionGroup", "")),
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
        # Use explicit cups count if present; otherwise derive from awards
        "cups": sum(1 for award in raw.get("awards", []) if (isinstance(award, str) and "Stanley Cup" in award) or (isinstance(award, dict) and "Stanley Cup" in (award.get("trophy") or {}).get("default", ""))),
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
        },
        "careerHighs": {
            "goals": _parse_int(raw.get("careerHighs", {}).get("goals"), 0),
            "points": _parse_int(raw.get("careerHighs", {}).get("points"), 0),
            "pim": _parse_int(raw.get("careerHighs", {}).get("pim"), 0),
        },
    }


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        source = json.load(f)

    if isinstance(source, dict):
        source = [source]

    normalized = [normalize_player(item) for item in source if isinstance(item, dict)]
    normalized = [item for item in normalized if item.get("id")]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=True, indent=2)

    print(f"Wrote {len(normalized)} players to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
