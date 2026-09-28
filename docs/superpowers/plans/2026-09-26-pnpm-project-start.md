# pnpm project:start Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax.

**Goal:** Migrate frontend to pnpm and add root `pnpm project:start` that auto-setups deps and starts frontend + backend.

**Architecture:** Root `package.json` + `scripts/project-start.mjs` with concurrently; frontend stays a separate pnpm package; backend uses local `.venv`.

**Tech Stack:** pnpm 11.24.0, concurrently, Node.js, Python 3 venv, uvicorn, Vite.

## Global Constraints

- Ports: frontend `:5173`, backend `127.0.0.1:8000`
- Auto-setup only when `frontend/node_modules` or `backend/.venv` missing
- Remove `frontend/package-lock.json`; use `pnpm-lock.yaml`
- Do not change app/API/Supabase runtime config

---

### Task 1: Root package + start script

**Files:**
- Create: `package.json`
- Create: `scripts/project-start.mjs`
- Modify: `.gitignore` (add `.venv/` if needed)

- [x] Create root `package.json` with `packageManager: pnpm@11.24.0`, script `project:start`, and `concurrently` as devDependency
- [x] Implement `scripts/project-start.mjs`: check/install frontend + backend deps, then run both via concurrently with `--kill-others-on-fail`
- [x] Ensure `.venv/` is gitignored
- [x] Prefer Python 3.10+ (Homebrew) over macOS system Python 3.9; upgrade pip before requirements install

### Task 2: Frontend pnpm migration

**Files:**
- Delete: `frontend/package-lock.json`
- Create: `frontend/pnpm-lock.yaml` (via install)

- [x] Remove `package-lock.json`
- [x] Run `pnpm install` in `frontend` and at repo root

### Task 3: README + verify

**Files:**
- Modify: `README.md`

- [x] Document prerequisites and `pnpm project:start`
- [x] Run `pnpm project:start` and confirm both servers respond
