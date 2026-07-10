## Plan: SQLite Canonical + Direct Site Data Pipeline

Use one command path from API explorer to produce backend-ready artifacts directly: a canonical SQLite raw store and a compact JSON runtime dataset. Backend reads SQLite first with JSON fallback during rollout. This removes manual copies and field-selection churn while keeping current frontend API contracts stable.

**Steps**
1. Phase A - Baseline and guardrails.
2. Record baseline counts from current flow (players processed, compact file count, backend /health playerCount) to compare after cutover. *blocks Phases B-E*
3. Confirm canonical artifact locations under c:/Users/cole/Documents/Code/nhlGame/backend/data/: players_raw.db and players_compact.json.
4. Confirm rollout policy: SQLite preferred, compact JSON fallback kept for one release window.
5. Phase B - API explorer writes canonical SQLite. *depends on Phase A*
6. In c:/Users/cole/Documents/Code/nhlGame/nhl-api-explorer/scripts/build-database.ts, add SQLite stage using deterministic upsert by player id.
7. Store full raw payload in raw_json plus indexed columns (player_id, name, position, last_season, updated_at).
8. Add pipeline_meta table containing schema version, built_at, source run id, and record counts.
9. Write DB directly to c:/Users/cole/Documents/Code/nhlGame/backend/data/players_raw.db.
10. Phase C - API explorer exports compact runtime JSON in same run. *depends on Phase B*
11. Keep current compact schema and NHL-only team normalization behavior compatible with existing backend predicates.
12. Write compact file to c:/Users/cole/Documents/Code/nhlGame/backend/data/players_compact.json.
13. Optional mirror for debugging only: c:/Users/cole/Documents/Code/nhlGame/nhl-api-explorer/public/data/players.json.
14. Add build summary output: total input players, DB rows written, compact rows written, skipped rows, error categories.
15. Phase D - Backend loader cutover with safe fallback. *depends on Phase C*
16. Update c:/Users/cole/Documents/Code/nhlGame/backend/app/game_service.py load order: SQLite first, compact JSON second.
17. Keep fallback branch and explicit warning log when fallback is active.
18. Add health metadata in c:/Users/cole/Documents/Code/nhlGame/backend/app/main.py (or metadata helper) to expose active data source and row count.
19. Remove duplicate runtime normalization where possible so build artifacts are treated as source-ready.
20. Phase E - Docs and deprecation. *parallel with late Phase D verification*
21. Update c:/Users/cole/Documents/Code/nhlGame/README.md and c:/Users/cole/Documents/Code/nhlGame/nhl-api-explorer/README.md with the new one-command build flow.
22. Mark c:/Users/cole/Documents/Code/nhlGame/scripts/build_data.py as transitional/deprecated, not primary.
23. Keep old path documented as emergency rollback for one release window.
24. Phase F - Verification gates and rollout. *depends on Phases C-D*
25. Add parity check gate: DB player count must equal compact JSON player count.
26. Add startup gate: backend should fail fast (except health) if neither DB nor compact fallback is valid.
27. Rollout in two passes: Pass 1 generate both formats + run fallback-ready backend, Pass 2 enforce SQLite default once parity stays green.

**Cutover Checklist (Local Dev)**
1. Install/update API explorer deps from c:/Users/cole/Documents/Code/nhlGame/nhl-api-explorer/package.json.
2. Run npm --prefix nhl-api-explorer run build-database to generate backend/data/players_raw.db and backend/data/players_compact.json.
3. Verify DB exists and has rows with a quick SQLite count query.
4. Start backend and verify /health reports expected player count and active source.
5. Start frontend and validate spin, eligible list, and scoring flows against backend.
6. Simulate rollback by temporarily moving DB file and confirming backend fallback to compact JSON still serves endpoints.

**Cutover Checklist (CI/CD)**
1. Data-build job: run npm --prefix nhl-api-explorer run build-database.
2. Parity job: assert DB row count equals compact JSON item count; fail pipeline on mismatch.
3. Backend test job: run API/service tests with DB present.
4. Fallback smoke job: run minimal startup test with DB hidden to confirm compact fallback still works during transition window.
5. Publish/deploy only if all four jobs pass.

**Relevant files**
- c:/Users/cole/Documents/Code/nhlGame/nhl-api-explorer/scripts/build-database.ts - canonical build path for both DB and compact outputs.
- c:/Users/cole/Documents/Code/nhlGame/backend/app/game_service.py - runtime loader precedence and fallback behavior.
- c:/Users/cole/Documents/Code/nhlGame/backend/app/main.py - health/source visibility.
- c:/Users/cole/Documents/Code/nhlGame/backend/data/ - final artifact destination.
- c:/Users/cole/Documents/Code/nhlGame/README.md - top-level runbook updates.
- c:/Users/cole/Documents/Code/nhlGame/nhl-api-explorer/README.md - API explorer pipeline docs.
- c:/Users/cole/Documents/Code/nhlGame/scripts/build_data.py - transitional script status note.

**Verification**
1. Artifact verification: both backend data artifacts are produced by one API explorer command.
2. Count verification: DB and compact counts match exactly.
3. API verification: /categories, /spin, /eligible, /score behave unchanged.
4. Frontend verification: no contract or UX regression in normal game loop.
5. Rollback verification: fallback path works if SQLite is unavailable.
6. Stability verification: parity and startup gates pass in CI for at least one release cycle before removing fallback.

**Decisions**
- Included: direct API explorer to backend data integration, SQLite canonical raw retention, compact compatibility export.
- Included: no reads of large data files during planning.
- Excluded: frontend direct SQLite reads in browser.
- Excluded: gameplay/category/scoring redesign.

**Further Considerations**
1. Driver choice in Node build script: prefer better-sqlite3 for deterministic build-time writes.
2. Retention mode: start with overwrite-per-build plus metadata versioning; defer historical snapshots unless audit needs increase.
3. Fallback removal trigger: remove JSON fallback only after one full release cycle of green parity checks and no source mismatch alerts.