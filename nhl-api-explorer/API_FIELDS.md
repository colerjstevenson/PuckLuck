# NHL API Fields Documentation

This document tracks the availability of player information from NHL API endpoints.

## Player Index Endpoint
**URL:** `https://api.nhle.com/stats/rest/en/players`

| Field | Source | Status | Notes |
|-------|--------|--------|-------|
| Player ID | playerId | Available | Unique identifier |
| Name | firstName, lastName | Available | Default language |
| Current Team | currentTeam | Available | Team abbreviation |
| Position | positionCode | Available | C, LW, RW, D, G |

## Player Landing Endpoint
**URL:** `https://api-web.nhle.com/v1/player/{playerId}/landing`

### Biography
| Feature | Source | Status | Notes |
|---------|--------|--------|-------|
| Birth Date | birthDate | Available | YYYY-MM-DD format |
| Birth Country | birthCountry | Available | Full country name |
| Birth City | birthCity | Available | City name |
| Height | heightInInches | Available | Inches |
| Weight | weightInPounds | Available | Pounds |
| Shoots/Catches | shootsCatches | Available | L or R |
| Headshot URL | headshot | Available | Player mugshot image URL |
| Jersey Number | sweaterNumber | Available | Player's current number |

### Career Information
| Feature | Source | Status | Notes |
|---------|--------|--------|-------|
| Seasons | seasonTotals | Available | List of seasons |
| Teams | seasonTotals.teamAbbrev | Available | Team abbreviations |
| Career Totals | careerTotals | Available | Regular season and playoffs |

### Draft Information
| Feature | Source | Status | Notes |
|---------|--------|--------|-------|
| Draft Year | draftDetails.year | Available | YYYY |
| Draft Round | draftDetails.round | Available | Round number |
| Draft Pick | draftDetails.pickInRound | Available | Pick number |

### Awards and Recognition
| Feature | Source | Status | Notes |
|---------|--------|--------|-------|
| Awards | awards | Available | List of awards with seasons |
| Hall of Fame | inHHOF | Available | 1 = in HHOF, 0 = not in HHOF |

### Season Statistics
| Feature | Source | Status | Notes |
|---------|--------|--------|-------|
| Season ID | seasonTotals.season | Available | YYYY |
| Games Played | seasonTotals.gamesPlayed | Available | Per season |
| Goals | seasonTotals.goals | Available | Per season |
| Assists | seasonTotals.assists | Available | Per season |
| Points | seasonTotals.points | Available | Per season |
| Plus/Minus | seasonTotals.plusMinus | Available | Per season |
| PIM | seasonTotals.pim | Available | Per season |
| Shots | seasonTotals.shots | Available | Per season |
| Shooting % | seasonTotals.shootingPctg | Available | Per season |
| Time on Ice | seasonTotals.avgToi | Available | Per season |
| Power Play Goals | seasonTotals.powerPlayGoals | Available | Per season |
| Power Play Points | seasonTotals.powerPlayPoints | Available | Per season |
| Short Handed Goals | seasonTotals.shorthandedGoals | Available | Per season |
| Short Handed Points | seasonTotals.shorthandedPoints | Available | Per season |
| Game Winning Goals | seasonTotals.gameWinningGoals | Available | Per season |
| OT Goals | seasonTotals.otGoals | Available | Per season |

## Skater Statistics Endpoint
**URL:** `https://api.nhle.com/stats/rest/en/skater/summary`

| Statistic | Source | Status | Notes |
|-----------|--------|--------|-------|
| Games Played | gamesPlayed | Available | |
| Goals | goals | Available | |
| Assists | assists | Available | |
| Points | points | Available | |
| Plus/Minus | plusMinus | Available | |
| Penalty Minutes | penaltyMinutes | Available | |
| Power Play Goals | ppGoals | Available | |
| Short Handed Goals | shGoals | Available | |
| Shots | shots | Available | |

## Goalie Statistics Endpoint
**URL:** `https://api.nhle.com/stats/rest/en/goalie/summary`

| Statistic | Source | Status | Notes |
|-----------|--------|--------|-------|
| Games Played | gamesPlayed | Available | |
| Wins | wins | Available | |
| Losses | losses | Available | |
| Saves | saves | Available | |
| Save Percentage | savePct | Available | |
| Goals Against Average | goalsAgainstAverage | Available | |
| Shutouts | shutouts | Available | |

## Category Feasibility Analysis

| Category | Feasible | Player Pool Estimate | Notes |
|----------|----------|---------------------|-------|
| Nationality | Yes | 1000+ per major country | birthCountry field |
| Team Played For | Yes | 100+ per team | teamsPlayedFor array |
| Era (Before 1980) | Yes | 5000+ | rookieSeason field |
| Draft Position | Yes | 100+ per category | draftRound/draftPick |
| Career Milestones | Yes | 100+ per milestone | careerStats |
| Awards | Yes | 500+ | awards array |
| Hall of Fame | Yes | ~200 | inHHOF field |
| Jersey Number | Yes | Varies by criteria | sweaterNumber field |
| Career Highs | Yes | All players | seasonTotals data |
| Stanley Cups | No | N/A | Requires external dataset |
