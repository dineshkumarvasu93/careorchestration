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
