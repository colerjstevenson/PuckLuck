from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

CURRENT_NHL_TEAMS = [
    "Anaheim Ducks",
    "Boston Bruins",
    "Buffalo Sabres",
    "Calgary Flames",
    "Carolina Hurricanes",
    "Chicago Blackhawks",
    "Colorado Avalanche",
    "Columbus Blue Jackets",
    "Dallas Stars",
    "Detroit Red Wings",
    "Edmonton Oilers",
    "Florida Panthers",
    "Los Angeles Kings",
    "Minnesota Wild",
    "Montreal Canadiens",
    "Nashville Predators",
    "New Jersey Devils",
    "New York Islanders",
    "New York Rangers",
    "Ottawa Senators",
    "Philadelphia Flyers",
    "Pittsburgh Penguins",
    "San Jose Sharks",
    "Seattle Kraken",
    "St. Louis Blues",
    "Tampa Bay Lightning",
    "Toronto Maple Leafs",
    "Utah Hockey Club",
    "Vancouver Canucks",
    "Vegas Golden Knights",
    "Washington Capitals",
    "Winnipeg Jets",
]

Player = dict
Predicate = Callable[[Player], bool]


@dataclass(frozen=True)
class CategoryDef:
    id: str
    label: str
    group: str
    weight: int
    predicate: Predicate


def _year_from_season(value: str | int | None) -> int | None:
    if value is None:
        return None
    text = str(value)
    if len(text) < 4:
        return None
    try:
        return int(text[:4])
    except ValueError:
        return None


def _age_now(player: Player) -> int | None:
    birth = player.get("birthDate")
    if not birth:
        return None
    try:
        y, m, d = map(int, str(birth).split("-"))
        born = date(y, m, d)
    except Exception:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _parse_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _team_category_id(team_name: str) -> str:
    slug = team_name.lower().replace(".", "").replace("-", " ")
    slug = "_".join(slug.split())
    return f"team_{slug}"


def _has_award(player: Player, award_name: str) -> bool:
    name = award_name.lower()
    return any(name in str(award).lower() for award in player.get("awards", []))


def _debut_age(player: Player) -> int | None:
    birth = player.get("birthDate")
    rookie = _year_from_season(player.get("rookieSeason"))
    if not birth or rookie is None:
        return None
    try:
        birth_year = int(str(birth).split("-")[0])
    except Exception:
        return None
    return rookie - birth_year


def _hof_eligible_not_inducted(player: Player) -> bool:
    if bool(player.get("inHHOF")):
        return False
    if bool(player.get("active")):
        return False
    last_year = _year_from_season(player.get("lastSeason"))
    if last_year is None:
        return False
    # HHOF generally requires players to be retired for at least three years.
    return last_year <= date.today().year - 3


def build_categories() -> list[CategoryDef]:
    original_six = {"BOSTON BRUINS", "CHICAGO BLACKHAWKS", "DETROIT RED WINGS", "MONTREAL CANADIENS", "NEW YORK RANGERS", "TORONTO MAPLE LEAFS"}

    def played_for_team(team_name: str) -> Predicate:
        team_name = team_name.upper()
        return lambda p: any(team_name in t.upper() for t in p.get("teamsPlayedFor", []))

    team_categories = [
        CategoryDef(_team_category_id(team_name), f"Played for {team_name}", "Team", 4, played_for_team(team_name))
        for team_name in CURRENT_NHL_TEAMS
    ]

    def played_in_decade(start_year: int) -> Predicate:
        end_year = start_year + 9

        def _pred(p: Player) -> bool:
            rookie = _year_from_season(p.get("rookieSeason"))
            last = _year_from_season(p.get("lastSeason"))
            if rookie is None or last is None:
                return False
            return rookie <= end_year and last >= start_year

        return _pred

    def natural_position(code: str) -> Predicate:
        wanted = code.upper()
        return lambda p: str(p.get("position", "")).upper() == wanted

    def jersey_between(min_value: int, max_value: int) -> Predicate:
        def _pred(p: Player) -> bool:
            number = p.get("sweaterNumber")
            if number is None:
                return False
            return min_value <= _parse_int(number) <= max_value

        return _pred

    categories = [
        CategoryDef("team_original_six", "Played for Original Six", "Team", 6, lambda p: any(t.upper() in original_six for t in p.get("teamsPlayedFor", []))),
        *team_categories,
        CategoryDef("franchise_multi", "3+ NHL franchises", "Team", 5, lambda p: len(set(p.get("teamsPlayedFor", []))) >= 3),
        CategoryDef("franchise_single", "Single-franchise career", "Team", 3, lambda p: len(set(p.get("teamsPlayedFor", []))) == 1),
        CategoryDef("era_1970s", "Played in the 1970s", "Era", 4, played_in_decade(1970)),
        CategoryDef("era_1980s", "Played in the 1980s", "Era", 5, played_in_decade(1980)),
        CategoryDef("era_1990s", "Played in the 1990s", "Era", 5, played_in_decade(1990)),
        CategoryDef("era_2000s", "Played in the 2000s", "Era", 5, played_in_decade(2000)),
        CategoryDef("era_2010s", "Played in the 2010s", "Era", 5, played_in_decade(2010)),
        CategoryDef("active", "Active player", "Era", 5, lambda p: bool(p.get("active"))),
        CategoryDef("retired", "Retired player", "Era", 5, lambda p: not bool(p.get("active"))),
        CategoryDef("debut_before_20", "Debuted before age 20", "Era", 3, lambda p: (_debut_age(p) or 99) < 20),
        CategoryDef("career_15", "Career length 15+ seasons", "Era", 4, lambda p: (_year_from_season(p.get("lastSeason")) or 0) - (_year_from_season(p.get("rookieSeason")) or 0) + 1 >= 15),
        CategoryDef("hof_eligible_not_inducted", "HHOF-eligible, not inducted", "Era", 3, _hof_eligible_not_inducted),
        CategoryDef("age_under_22", "Under 22", "Era", 2, lambda p: (_age_now(p) or 100) < 22),
        CategoryDef("age_over_35", "Over 35", "Era", 4, lambda p: (_age_now(p) or 0) > 35),
        CategoryDef("nat_can", "Canadian", "Nationality", 8, lambda p: p.get("birthCountry") == "CAN"),
        CategoryDef("nat_usa", "American", "Nationality", 6, lambda p: p.get("birthCountry") == "USA"),
        CategoryDef("nat_swe", "Swedish", "Nationality", 4, lambda p: p.get("birthCountry") == "SWE"),
        CategoryDef("nat_rus", "Russian", "Nationality", 4, lambda p: p.get("birthCountry") == "RUS"),
        CategoryDef("nat_fin", "Finnish", "Nationality", 4, lambda p: p.get("birthCountry") == "FIN"),
        CategoryDef("nat_cze", "Czech", "Nationality", 3, lambda p: p.get("birthCountry") == "CZE"),
        CategoryDef("draft_first_round", "First-round pick", "Draft", 4, lambda p: _parse_int(p.get("draftRound")) == 1),
        CategoryDef("draft_top_5", "Top-5 overall pick", "Draft", 3, lambda p: 0 < _parse_int(p.get("draftPick")) <= 5),
        CategoryDef("draft_late_round", "Late-round pick (4+)", "Draft", 3, lambda p: _parse_int(p.get("draftRound")) >= 4),
        CategoryDef("draft_undrafted", "Undrafted", "Draft", 4, lambda p: _parse_int(p.get("draftRound")) == 0),
        CategoryDef("pos_center", "Center", "Position", 4, natural_position("C")),
        CategoryDef("pos_winger", "Winger", "Position", 4, lambda p: str(p.get("position", "")).upper() in {"L", "R"}),
        CategoryDef("pos_defense", "Defenceman", "Position", 4, natural_position("D")),
        CategoryDef("pos_goalie", "Goalie", "Position", 4, natural_position("G")),
        CategoryDef("shot_left_proxy", "Left shot (proxy)", "Position", 2, natural_position("L")),
        CategoryDef("shot_right_proxy", "Right shot (proxy)", "Position", 2, natural_position("R")),
        CategoryDef("jersey_le_20", "Jersey number <= 20", "Position", 3, jersey_between(0, 20)),
        CategoryDef("jersey_21_49", "Jersey number 21-49", "Position", 3, jersey_between(21, 49)),
        CategoryDef("jersey_ge_50", "Jersey number 50+", "Position", 3, lambda p: (_parse_int(p.get("sweaterNumber"), -1)) >= 50),
        CategoryDef("hof_yes", "Hall of Fame inductee", "Awards", 4, lambda p: bool(p.get("inHHOF"))),
        CategoryDef("cup_yes", "Stanley Cup champion", "Awards", 7, lambda p: int(p.get("cups", 0)) > 0 or any("Stanley Cup" in a for a in p.get("awards", []))),
        CategoryDef("cup_no", "Never won a cup", "Awards", 6, lambda p: int(p.get("cups", 0)) == 0 and all("Stanley Cup" not in a for a in p.get("awards", []))),
        CategoryDef("award_hart", "Hart Trophy winner", "Awards", 3, lambda p: _has_award(p, "Hart Trophy")),
        CategoryDef("award_norris", "Norris Trophy winner", "Awards", 3, lambda p: _has_award(p, "Norris Trophy")),
        CategoryDef("award_vezina", "Vezina Trophy winner", "Awards", 3, lambda p: _has_award(p, "Vezina Trophy")),
        CategoryDef("award_calder", "Calder Trophy winner", "Awards", 3, lambda p: _has_award(p, "Calder Trophy")),
        CategoryDef("points_1000", "1000+ career points", "Milestones", 4, lambda p: int(p.get("stats", {}).get("points", 0)) >= 1000),
        CategoryDef("goals_500", "500+ career goals", "Milestones", 3, lambda p: int(p.get("stats", {}).get("goals", 0)) >= 500),
        CategoryDef("assists_700", "700+ career assists", "Milestones", 3, lambda p: int(p.get("stats", {}).get("assists", 0)) >= 700),
        CategoryDef("goalie_wins_300", "300+ career wins (goalie)", "Milestones", 2, lambda p: str(p.get("position", "")).upper() == "G" and _parse_int(p.get("stats", {}).get("wins", 0)) >= 300),
        CategoryDef("goalie_sv_pct_915", "Career save percentage >= .915", "Milestones", 2, lambda p: str(p.get("position", "")).upper() == "G" and _parse_float(p.get("stats", {}).get("savePctg", 0.0)) >= 0.915),
        CategoryDef("games_lt_200", "Under 200 games played", "Milestones", 3, lambda p: int(p.get("stats", {}).get("gamesPlayed", 0)) < 200),
        CategoryDef("points_lt_500", "Under 500 career points", "Milestones", 3, lambda p: int(p.get("stats", {}).get("points", 0)) < 500),
        CategoryDef("season_50g", "50-goal season", "Milestones", 3, lambda p: int(p.get("careerHighs", {}).get("goals", 0)) >= 50),
        CategoryDef("season_100p", "100-point season", "Milestones", 3, lambda p: int(p.get("careerHighs", {}).get("points", 0)) >= 100),
        CategoryDef("season_30w_goalie_proxy", "30-win goalie season (proxy)", "Milestones", 2, lambda p: str(p.get("position", "")).upper() == "G" and _parse_int(p.get("stats", {}).get("wins", 0)) >= 30),
        CategoryDef("season_150pim", "150+ PIM in a season", "Milestones", 2, lambda p: int(p.get("careerHighs", {}).get("pim", 0)) >= 150),
        CategoryDef("season_lt_30g", "Never had 30 goals in a season", "Milestones", 2, lambda p: int(p.get("careerHighs", {}).get("goals", 0)) < 30),
        CategoryDef("season_lt_50p", "Never had 50 points in a season", "Milestones", 2, lambda p: int(p.get("careerHighs", {}).get("points", 0)) < 50),
        CategoryDef("goalie_scored", "Scored as a goalie", "Milestones", 1, lambda p: str(p.get("position", "")).upper() == "G" and int(p.get("stats", {}).get("goals", 0)) > 0),
    ]
    return categories
