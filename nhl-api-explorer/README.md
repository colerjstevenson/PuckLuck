# NHL API Explorer

This project is part of Phase 0 of the NHL Ultimate Team Builder. It's designed to explore and validate NHL API endpoints to determine what data is available for the game.

## Setup

1. Install dependencies:
```bash
npm install
```

## Scripts

### Download All Players
Fetches the complete list of NHL players from the stats API.

```bash
npm run download-players
```

Output: `output/raw/all-players.json`

### Test Player
Fetches detailed information for a specific player and displays a summary.

```bash
npm run test-player [playerId]
```

Default playerId: 8478402 (Connor McDavid)

Output: 
- `cache/players/{playerId}.json` (cached raw data)
- Console summary

### Inspect Player
Processes a player's data into our data model and saves both raw and processed versions.

```bash
npm run inspect-player [playerId]
```

Output:
- `output/raw/{playerId}.json` (raw data)
- `output/processed/{playerId}.json` (processed data)
- Console summary

### Build Database
Creates canonical and runtime-ready player datasets from cached player payloads.

```bash
npm run build-database
```

Outputs:
- `../backend/data/players_raw.db` (canonical raw payload store)
- `../backend/data/players_compact.json` (runtime compact dataset)
- `public/data/players.json` (debug/inspection mirror)

Build guarantees:
- Deterministic upsert keyed by `player_id`
- `pipeline_meta` records schema/build metadata and counts
- Parity gate fails the build if DB row count and compact row count diverge
- Summary logs include input count, written counts, skipped rows, and categorized errors

## Project Structure

```
nhl-api-explorer/
├── scripts/
│   ├── test-player.ts
│   ├── download-players.ts
│   ├── inspect-player.ts
│   └── build-database.ts
├── cache/
│   └── players/
├── output/
│   ├── raw/
│   └── processed/
├── public/
│   └── data/
├── API_FIELDS.md
└── README.md
```

## Phase 0 Completion Checklist

- [x] NHL endpoints tested
- [x] Player list downloaded
- [x] Player details verified
- [x] Statistics verified
- [x] Categories tested
- [x] Missing datasets identified
- [x] Final database schema created

