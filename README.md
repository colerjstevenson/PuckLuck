# NHL Classic Challenge

A hockey-themed web game inspired by your plan: spin two categories, choose eligible players, and build a 6-slot lineup (3F, 2D, 1G) with off-position penalties and final score breakdown.

## Architecture

- Frontend: React + TypeScript + Vite (static app for GitHub Pages)
- Backend: FastAPI (Python runtime API)
- Data pipeline: API explorer builds canonical `backend/data/players_raw.db` and runtime `backend/data/players_compact.json`

This matches the required deployment split:
- GitHub Pages serves the frontend
- Python API is deployed on a Python-capable host (Render, Railway, Fly.io)

## Project Layout

- `frontend/` static UI app
- `backend/` FastAPI runtime service
- `nhl-api-explorer/scripts/build-database.ts` canonical data builder
- `scripts/build_data.py` legacy fallback compact data builder
- `.github/workflows/frontend-pages.yml` frontend deploy workflow
- `.github/workflows/backend-api.yml` backend CI workflow

## Local Development

### 1) Build canonical and compact data

```powershell
cd nhl-api-explorer
npm.cmd install
npm.cmd run build-database
```

Outputs:
- `backend/data/players_raw.db`
- `backend/data/players_compact.json`

Runtime load order:
1. SQLite canonical store: `backend/data/players_raw.db`
2. Compact fallback: `backend/data/players_compact.json`

During the transition window, the compact fallback remains enabled for rollback safety.

### 2) Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend default URL: `http://127.0.0.1:8000`

### 3) Run frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend dev URL: `http://127.0.0.1:5173`

Set `VITE_API_BASE_URL` in `.env` if backend runs on another host.

## API Endpoints

- `GET /health`
- `GET /categories`
- `POST /spin`
- `POST /eligible`
- `GET /player/{player_id}`
- `POST /score`

`GET /health` now reports:
- `dataSource` (active source)
- `sourceRowCount` (rows read from the selected source)
- `dataReady` (whether gameplay endpoints are enabled)

## GitHub Pages Deployment

1. Push repo to GitHub.
2. In repository settings, enable GitHub Pages with GitHub Actions.
3. Add repository secret `VITE_API_BASE_URL` pointing to your deployed Python API.
4. Push to `main` to trigger `.github/workflows/frontend-pages.yml`.

## Backend Deployment

Use `backend/Dockerfile` on Render/Railway/Fly.

Set environment variable `FRONTEND_ORIGINS` to your GitHub Pages URL, for example:

`https://<username>.github.io`

## Notes

- Classic mode is implemented first, as requested.
- Pro mode is intentionally deferred.
- Categories requiring unavailable schema fields (for example shot handedness) are not yet active.
