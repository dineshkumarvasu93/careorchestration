# GitHub Actions CI/CD Pipelines

## Overview

This directory contains GitHub Actions workflow files for the **Unified Patient Access & Clinical Intelligence Platform**.

The pipeline targets three deployment platforms:

| Layer | Platform | Notes |
|-------|----------|-------|
| **Backend API** | [Railway](https://railway.com) | .NET 9 API deployed from source via Railway CLI |
| **Database** | [Supabase](https://supabase.com) | Managed PostgreSQL -- EF Core migrations per environment |
| **Frontend SPA** | [InfinityFree](https://dash.infinityfree.com) | React build uploaded via `lftp` FTP |

No Docker. No container registry. Railway builds from source using Nixpacks/buildpacks.

---

## Workflow

All stages are consolidated into a single file: **`pipeline.yml`** (also copied to `.github/workflows/pipeline.yml`).

| File | Trigger | Stages covered |
|------|---------|----------------|
| `pipeline.yml` | push / PR / tag / weekly schedule | CI · Dev CD · QA CD · Staging CD · Prod CD · Security |

### Stage summary

| Stage | Jobs (prefix) | Trigger condition |
|-------|---------------|-------------------|
| **CI** | `[CI] Build API`, `[CI] Build Frontend`, `[CI] Lint`, `[CI] Unit Tests`, `[CI] E2E Tests`, `[CI] PITR Smoke` | Every push & PR (not schedule) |
| **Security** | `[Security] CodeQL`, `[Security] Secrets Scan`, `[Security] SCA` | Push to main/develop, PRs, weekly schedule |
| **Dev CD** | `[Dev] Migrate DB`, `[Dev] Deploy API`, `[Dev] Deploy Frontend` | Push to `develop` |
| **QA CD** | `[QA] Migrate DB`, `[QA] Deploy API`, `[QA] Deploy Frontend` | After Dev CD on `develop` |
| **Staging CD** | `[Staging] Migrate DB`, `[Staging] Deploy API`, `[Staging] Deploy Frontend`, `[Staging] Smoke Test`, `[Staging] Rollback` | Push to `main` (approval gate) |
| **Prod CD** | `[Prod] Migrate DB`, `[Prod] Deploy API (canary)`, `[Prod] Promote`, `[Prod] Deploy Frontend`, `[Prod] Rollback` | Tag `v*.*.*` (approval gate) |

---

## Branch Strategy

| Branch | Purpose | CD triggered |
|--------|---------|--------------|
| `feature/*` | Feature development | CI only |
| `develop` | Integration branch | Dev CD → QA CD (chained) |
| `main` | Stable / release candidate | Staging CD (approval gated) |
| `v*.*.*` tag | Production release | Prod CD (approval gated, canary) |

---

## Required GitHub Secrets

Configure all secrets at: **Repo Settings --> Secrets and variables --> Actions**

| Secret | Scope | Description |
|--------|-------|-------------|
| `CI_JWT_SIGNING_KEY` | All | 32+ char random string for CI test JWT signing |
| `RAILWAY_TOKEN` | CD workflows | Railway API token (Settings --> Tokens) |
| `RAILWAY_PROJECT_ID` | CD workflows | Railway project ID (project Settings) |
| `SUPABASE_DEV_CONNECTION_STRING` | cd-dev | `Host=db.xxx.supabase.co;Port=5432;Database=postgres;Username=postgres;Password=xxx;SSL Mode=Require` |
| `SUPABASE_QA_CONNECTION_STRING` | cd-qa | QA Supabase project connection string |
| `SUPABASE_STAGING_CONNECTION_STRING` | cd-staging | Staging Supabase project connection string |
| `SUPABASE_PROD_CONNECTION_STRING` | cd-prod | Production Supabase project connection string |
| `DEV_API_BASE_URL` | cd-dev | Railway dev API URL, e.g. `https://api-dev.up.railway.app` |
| `QA_API_BASE_URL` | cd-qa | Railway qa API URL |
| `STAGING_API_BASE_URL` | cd-staging | Railway staging API URL |
| `STAGING_FRONTEND_URL` | cd-staging | InfinityFree staging URL |
| `PROD_API_BASE_URL` | cd-prod | Railway production API URL |
| `PROD_FRONTEND_URL` | cd-prod | InfinityFree production URL |
| `INFINITYFREE_FTP_HOST_DEV` | cd-dev | FTP host for dev site |
| `INFINITYFREE_FTP_USERNAME_DEV` | cd-dev | FTP username for dev |
| `INFINITYFREE_FTP_PASSWORD_DEV` | cd-dev | FTP password for dev |
| `INFINITYFREE_FTP_PATH_DEV` | cd-dev | Remote path, e.g. `/htdocs` |
| `INFINITYFREE_FTP_HOST_QA` | cd-qa | FTP host for qa site |
| `INFINITYFREE_FTP_USERNAME_QA` | cd-qa | FTP username for qa |
| `INFINITYFREE_FTP_PASSWORD_QA` | cd-qa | FTP password for qa |
| `INFINITYFREE_FTP_PATH_QA` | cd-qa | Remote path for qa |
| `INFINITYFREE_FTP_HOST_STAGING` | cd-staging | FTP host for staging site |
| `INFINITYFREE_FTP_USERNAME_STAGING` | cd-staging | FTP username for staging |
| `INFINITYFREE_FTP_PASSWORD_STAGING` | cd-staging | FTP password for staging |
| `INFINITYFREE_FTP_PATH_STAGING` | cd-staging | Remote path for staging |
| `INFINITYFREE_FTP_HOST_PROD` | cd-prod | FTP host for production site |
| `INFINITYFREE_FTP_USERNAME_PROD` | cd-prod | FTP username for production |
| `INFINITYFREE_FTP_PASSWORD_PROD` | cd-prod | FTP password for production |
| `INFINITYFREE_FTP_PATH_PROD` | cd-prod | Remote path for production |
| `SLACK_WEBHOOK_URL` | cd-staging, cd-prod | Slack incoming webhook (optional but recommended) |
| `SNYK_TOKEN` | security-scan | Snyk API token (optional; scan continues without it) |

---

## GitHub Environments Setup

Go to: **Repo Settings --> Environments --> New environment**

### Environment: `dev`
- No protection rules required
- Auto-deploys on every push to `develop`

### Environment: `qa`
- No protection rules required
- Auto-deploys after `Deploy to Dev` workflow succeeds

### Environment: `staging`
- Add **Required reviewers** (at least 1 approver)
- Deployments paused until reviewer approves in the Actions UI

### Environment: `production`
- Add **Required reviewers** (at least 1 approver)
- Set **Deployment branch filter**: restrict to branch `main`
- Set **Tag pattern**: `v*` to allow only version tags
- Canary deploy pattern: 10% traffic --> 5 min observation --> 100% promotion

---

## Railway Setup

1. Create a Railway account at [railway.com](https://railway.com)
2. Create a new **Project** for this application
3. Inside the project, create **4 environments**: `dev`, `qa`, `staging`, `production`
4. For each environment, add a **Service** named `api` pointing to the repository root
5. Set Railway environment variables per environment (e.g. `DATABASE_URL`, `ASPNETCORE_ENVIRONMENT`)
6. Copy your **Railway Token**:
   - Go to Railway Dashboard --> Account Settings --> Tokens
   - Create a new token and add it as `RAILWAY_TOKEN` secret in GitHub
7. Copy your **Railway Project ID**:
   - Open project Settings in Railway
   - Copy the Project ID from the URL or settings panel
   - Add it as `RAILWAY_PROJECT_ID` secret in GitHub

> Railway uses Nixpacks to auto-detect and build .NET 9 projects from source. No Dockerfile needed.

---

## Supabase Setup

1. Create a Supabase account at [supabase.com](https://supabase.com)
2. Create **4 Supabase projects** -- one per environment (dev, qa, staging, production)
3. For each project, get the connection string:
   - Go to **Project Settings --> Database --> Connection string**
   - Select **.NET** format: `Host=db.xxx.supabase.co;Port=5432;Database=postgres;Username=postgres;Password=xxx;SSL Mode=Require`
4. Add each connection string as the corresponding GitHub secret:
   - `SUPABASE_DEV_CONNECTION_STRING`
   - `SUPABASE_QA_CONNECTION_STRING`
   - `SUPABASE_STAGING_CONNECTION_STRING`
   - `SUPABASE_PROD_CONNECTION_STRING`

> Connection strings contain passwords -- always store them as encrypted GitHub secrets. Never commit to source code.

> CI unit tests use ephemeral `pgvector/pgvector:pg16` service containers -- Supabase is never used in CI.

---

## InfinityFree Setup

1. Create an account at [infinityfree.com](https://www.infinityfree.com)
2. Create a **hosting account** (free plan) for each environment that needs a separate subdomain/domain
3. Find FTP credentials in the **Control Panel --> FTP Accounts**:
   - FTP Host: shown in Control Panel (e.g. `ftpupload.net`)
   - FTP Username: your account username
   - FTP Password: set in Control Panel
   - Default FTP path: `/htdocs`
4. Add per-environment FTP secrets to GitHub (see secrets table above)
5. The workflow creates a `.htaccess` file in `client/dist/` before upload to enable SPA client-side routing:

```apache
Options -MultiViews
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^ index.html [QSA,L]
```

---

## Security Gates

- **No `permissions: write-all`** -- every workflow uses least-privilege permissions
- **All secrets via `${{ secrets.NAME }}`** -- zero hardcoded credentials
- **`actions/*` pinned to `@v4`** -- no floating version tags
- **CodeQL SAST** runs on C# and JavaScript on every push to main/develop
- **Gitleaks** scans for leaked secrets with full git history (`fetch-depth: 0`)
- **`npm audit --audit-level=high`** and **`dotnet list package --vulnerable`** on every CI run

---

## Rollback Procedures

### Staging rollback (automatic)
On smoke test failure after staging deploy, the `rollback-staging` job runs automatically:
```bash
railway rollback --environment staging --service api
```

### Production rollback (automatic)
On canary or full-deploy failure, the `rollback-prod` job runs automatically:
```bash
railway rollback --environment production --service api
```

### Manual rollback
To manually roll back any environment:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Authenticate
railway login

# Rollback
railway rollback --environment <env> --service api
```

---

## Local Development

```bash
# Backend (from repo root)
dotnet restore PropelIQ-Stub-Copilot.sln
dotnet run --project api/Api.csproj

# Frontend (from client/)
npm install
npm run dev

# EF Core migrations (local)
dotnet tool restore
dotnet ef database update --project api/Api.csproj
```

For local database, use Docker:
```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=localdev pgvector/pgvector:pg16
```

Set `DATABASE_URL` in `api/appsettings.Development.json` to your local connection string.
