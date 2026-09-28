# Design: pnpm + `pnpm project:start`

Date: 2026-09-26  
Status: approved (pending implementation plan)

## Goal

Migrate the JS tooling to pnpm and provide a single root command that starts both the Vue frontend and the FastAPI backend, with automatic dependency setup when needed.

## Requirements

- `pnpm project:start` starts **frontend and backend** in parallel.
- If `frontend/node_modules` is missing → run `pnpm install` in `frontend`.
- If `backend/.venv` is missing → create venv and `pip install -r requirements.txt`.
- Ctrl+C stops both processes.
- Existing ports stay: frontend Vite `:5173`, backend uvicorn `127.0.0.1:8000`.
- Frontend migrates from npm (`package-lock.json`) to pnpm (`pnpm-lock.yaml`).

## Non-goals

- Full pnpm workspace / Turborepo / Nx.
- Changing app runtime config, API URLs, or Supabase env vars.
- Dockerizing the stack.
- Auto-creating `.env` files (they already exist locally and remain gitignored).

## Architecture

```
fin-assistant/
  package.json              # root scripts + packageManager
  scripts/project-start.mjs # setup checks + concurrent start
  frontend/                 # Vue app (pnpm)
  backend/                  # FastAPI (Python venv)
  README.md                 # one-command run instructions
```

Root `package.json` exposes:

```json
{
  "scripts": {
    "project:start": "node scripts/project-start.mjs"
  }
}
```

`packageManager` is set to the installed pnpm version (e.g. `pnpm@11.24.0`) for Corepack.

## Start script behavior

`scripts/project-start.mjs`:

1. **Frontend deps**: if `frontend/node_modules` does not exist, run `pnpm install` with cwd `frontend`.
2. **Backend deps**: if `backend/.venv` does not exist:
   - `python3 -m venv .venv` in `backend`
   - `.venv/bin/pip install -r requirements.txt`
3. **Run concurrently** (via `concurrently` from root `devDependencies`):
   - name `web`: `pnpm --dir frontend dev`
   - name `api`: `backend/.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000` with cwd `backend`
4. Propagate exit / SIGINT so both children terminate.

On subsequent runs, when deps already exist, skip install and go straight to step 3.

## Frontend migration

- Delete `frontend/package-lock.json`.
- Add `frontend/pnpm-lock.yaml` by running `pnpm install` in `frontend`.
- Keep `frontend/package.json` scripts (`dev`, `build`, `preview`) unchanged.
- Optionally add `frontend/.npmrc` only if needed (prefer defaults).

## Root dependencies

- `concurrently` as a root `devDependency` for parallel process management and labeled logs.

## Documentation

Update root `README.md` (currently empty) with:

1. Prerequisites: Node 18+, pnpm, Python 3.10+
2. Env: `frontend/.env` and `backend/.env` must exist
3. Run: `pnpm project:start`
4. URLs: app `http://localhost:5173`, API `http://127.0.0.1:8000`, docs `http://127.0.0.1:8000/docs`

## Error handling

- If `pnpm`, `python3`, or `pip` install fails, exit non-zero with a clear message; do not start the other process after a failed setup step.
- If either runtime process exits unexpectedly, terminate the other (concurrently default / `--kill-others-on-fail`).

## Testing (manual)

1. Fresh clone simulation: remove `frontend/node_modules` and `backend/.venv`, run `pnpm project:start` → installs then both servers up.
2. Second run: no reinstall spam, both servers up quickly.
3. Ctrl+C stops both.
4. Frontend loads; API root returns active status.
