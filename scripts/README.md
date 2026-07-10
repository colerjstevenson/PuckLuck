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
