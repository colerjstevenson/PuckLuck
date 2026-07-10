# Project Edit Outline (Data Files Excluded)

This file maps **what to edit** based on the type of change you want to make.

Scope notes:
- Large data files are intentionally excluded.
- This covers app logic, UI, APIs, types, config, and tooling.

---

## 1) Backend API behavior

### Change API routes, request/response handlers, server startup
- `backend/app/main.py`

### Change game rules, validation, or game flow logic
- `backend/app/game_service.py`

### Change scoring/category logic
- `backend/app/categories.py`

### Change backend data models / schemas
- `backend/app/models.py`

### Change backend package/module exports
- `backend/app/__init__.py`

---

## 2) Frontend application behavior

### Change app-level state, page structure, flow between components
- `frontend/src/App.tsx`

### Change frontend API calls (endpoints, payload shapes, error handling)
- `frontend/src/api.ts`

### Change shared frontend TypeScript types/interfaces
- `frontend/src/types.ts`

### Change app bootstrap/mount behavior
- `frontend/src/main.tsx`

### Change global frontend styles
- `frontend/src/styles.css`

### Change category tile UI/interaction
- `frontend/src/components/CategoryTile.tsx`

### Change rink board UI/game board rendering
- `frontend/src/components/RinkBoard.tsx`

### Change score modal behavior/UI
- `frontend/src/components/ScoreModal.tsx`

---

## 3) Frontend static assets and HTML shell

### Change root HTML template (title, root node, meta tags)
- `frontend/index.html`

### Change static public assets usage/paths
- `frontend/public/` (asset files)

---

## 4) Frontend toolchain/config

### Change frontend npm scripts/dependencies
- `frontend/package.json`

### Change TypeScript compiler options
- `frontend/tsconfig.json`

### Change Vite dev/build config (base path, plugins, aliases)
- `frontend/vite.config.ts`

### Change Vite env type declarations
- `frontend/src/vite-env.d.ts`

---

## 5) Backend runtime/container/dependencies

### Change Python dependencies
- `backend/requirements.txt`

### Change backend container image/build/run behavior
- `backend/Dockerfile`

---

## 6) Data build pipeline (code only, not data content)

### Change data generation/transformation logic
- `scripts/build_data.py`

### Change script usage documentation
- `scripts/README.md`

---

## 7) Project-level docs and planning

### Change general project documentation
- `README.md`

### Change implementation plan / notes
- `plan.md`

---

## 8) Quick edit recipes (common tasks)

### Add a new backend field that appears in UI
1. Edit backend model/schema: `backend/app/models.py`
2. Populate/use it in logic: `backend/app/game_service.py` (and/or `backend/app/categories.py`)
3. Return it in API route response: `backend/app/main.py`
4. Add/update frontend types: `frontend/src/types.ts`
5. Update frontend API parsing/calls: `frontend/src/api.ts`
6. Render it in UI: relevant component(s) in `frontend/src/components/` and/or `frontend/src/App.tsx`

### Add a new UI widget/component
1. Create/update component in `frontend/src/components/`
2. Wire it into page/state in `frontend/src/App.tsx`
3. Add style changes in `frontend/src/styles.css`
4. Add/update any required shared types in `frontend/src/types.ts`

### Change API endpoint path or shape
1. Backend route/handler: `backend/app/main.py`
2. Backend response model/shape: `backend/app/models.py`
3. Frontend API client: `frontend/src/api.ts`
4. Frontend consuming types/components: `frontend/src/types.ts`, then relevant component files

---

## 9) Ownership summary by folder

### Backend code
- `backend/app/`

### Frontend code
- `frontend/src/`

### Frontend static shell/assets
- `frontend/index.html`, `frontend/public/`

### Build and runtime config
- `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `backend/requirements.txt`, `backend/Dockerfile`

### Scripts and docs
- `scripts/`, `README.md`, `plan.md`
