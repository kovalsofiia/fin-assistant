# FOP Assistant

Vue 3 (Vite) frontend + FastAPI backend on Supabase.

## Prerequisites

- Node.js 18+
- [pnpm](https://pnpm.io/) 11+
- Python 3.10+ (Homebrew `python3.12` / newer preferred over macOS system Python 3.9)

## Environment

Create (or keep) local env files:

- `frontend/.env` — `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- `backend/.env` — `SUPABASE_URL`, `SUPABASE_KEY`

## Run

From the repo root:

```bash
pnpm project:start
```

On first run this installs frontend/root npm deps and creates `backend/.venv` if needed, then starts both servers.

- App: http://localhost:5173
- API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

Stop with `Ctrl+C`.
