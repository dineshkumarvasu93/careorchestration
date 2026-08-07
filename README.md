# Care Orchestration Local Setup

This guide explains how to run backend and frontend locally from the repository root.

## Prerequisites

1. Windows PowerShell
2. Python launcher (`py`) with Python 3.14+
3. Node.js and npm

Verify tools:

```powershell
py --version
node --version
npm --version
```

Note: On this machine, `python` may not be available via PATH alias. Use `py` commands.

## Project Structure

- Backend app: [backend](backend)
- Frontend static pages: [frontend](frontend)

## Tech Stack

- Backend framework: FastAPI 0.115.0
- ASGI server: Uvicorn 0.30.6
- Backend language/runtime: Python 3.14+
- Frontend: Static HTML, CSS, JavaScript
- Frontend local server: http-server 14.1.1 (via npx)
- Backend testing: pytest 8.3.3
- Frontend E2E testing: Playwright (TypeScript)

## Backend Setup And Run

From repository root:

```powershell
py -m pip install -r backend/requirements.txt
Set-Location backend
py -m uvicorn app.main:app --reload --port 8000
```

Backend URLs:

- Health: http://localhost:8000/health
- Ready: http://localhost:8000/ready
- API base: http://localhost:8000/api/v1

## Frontend Setup And Run

Run frontend in a second terminal from repository root:

```powershell
npx http-server frontend -p 5500 -c-1
```

If prompted `Ok to proceed?`, type `y` and press Enter.

Frontend URLs:

- Raw CKD profile: http://localhost:5500/raw-ckd-profile.html
- Workflow tracking: http://localhost:5500/workflow-tracking.html
- Rule config dashboard: http://localhost:5500/rule-config-dashboard.html
- Analytics dashboard: http://localhost:5500/analytics-dashboard.html

## Run Backend And Frontend Together

Use two terminals:

1. Terminal 1 (backend):

```powershell
Set-Location backend
py -m uvicorn app.main:app --reload --port 8000
```

2. Terminal 2 (frontend):

```powershell
npx http-server frontend -p 5500 -c-1
```

Then open frontend URLs listed above.

## Run With Docker (Postgres + pgAdmin)

The full stack can run in containers, with rule configuration persisted to
Postgres and inspectable in pgAdmin. This works with **Docker Desktop** and
**Rancher Desktop**.

### Rancher Desktop notes

- In Rancher Desktop, choose the **dockerd (moby)** container engine
  (Preferences → Container Engine) so the `docker` CLI and `docker compose`
  work directly.
- If you use the **containerd** engine instead, substitute `nerdctl compose`
  for `docker compose` in the commands below.

### Start the stack

From the repository root:

```powershell
docker compose up --build
```

Services and URLs:

- Backend API: http://localhost:8000/health
- Frontend dashboards: http://localhost:5500/us017/rule-config-dashboard.html
- pgAdmin: http://localhost:5050 (login `admin@example.com` / `admin`)
- Postgres: `localhost:5432` (db `care_orchestration`, user `care`)

Configuration defaults live in `.env.example`; copy it to `.env` to override
ports, credentials, or the database name.

### How the app connects to the database

- The `backend` service receives `DATABASE_URL` pointing at the `postgres`
  service over the Docker network, so the FastAPI app talks to Postgres by the
  service hostname `postgres` (no localhost).
- When `DATABASE_URL` is **not** set (e.g. the host `uvicorn` workflow above),
  the backend automatically falls back to the built-in in-memory rule store, so
  local development and tests need no database.

### Inspect rule data in pgAdmin

1. Open http://localhost:5050 and log in.
2. The "Care Orchestration" server is pre-registered; enter the Postgres
   password (`care_password` by default) when prompted.
3. Browse `care_orchestration` → Schemas → public → Tables:
   - `rule_versions` — every published rule set (payload stored as JSON)
   - `rule_active_state` — the currently active version

### Stop the stack

```powershell
docker compose down
```

Add `-v` to also remove the Postgres data volume (`docker compose down -v`).

## Flutter Drag-and-Drop Component

The rule-config dashboard is an HTML page, but its **drag-and-drop ruleset
builder is a Flutter Web component** embedded as an `<iframe>`. The Flutter
island (in [flutter_rule_config](flutter_rule_config)) only handles the
drag-and-drop; it reports the composed ruleset to the HTML page via
`postMessage`, and the HTML page does the publish/activate/version calls.

Requires the Flutter SDK. Build the component and drop it into the frontend:

```powershell
./scripts/build-flutter-dnd.ps1
```

This runs `flutter build web --base-href /us017/flutter/` and copies the output
to `frontend/us017/flutter/`, where the dashboard's iframe loads it. Then open
the Rule config dashboard (Docker `frontend` service or `npx http-server
frontend`). Until you build it, the rest of the dashboard works and the
component area is empty.

The backend enables CORS for local development so the browser can call
`http://localhost:8000` cross-origin. See
[flutter_rule_config/README.md](flutter_rule_config/README.md) for the standalone
dev workflow and interop details.

## Optional: Run Backend Tests

From repository root:

```powershell
py -m pytest backend/tests -q
```

## Common Troubleshooting

1. `No module named uvicorn`
- Install backend requirements again:

```powershell
py -m pip install -r backend/requirements.txt
```

2. `python` command not found
- Use `py` instead of `python`.

3. Port already in use
- Change ports:

```powershell
py -m uvicorn app.main:app --reload --port 8010
npx http-server frontend -p 5510 -c-1
```

4. Frontend cannot reach backend
- Confirm backend is running on port 8000.
- Confirm browser can open http://localhost:8000/health
