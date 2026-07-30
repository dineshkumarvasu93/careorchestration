---
title: CI/CD Pipeline Specification -- Unified Patient Access & Clinical Intelligence Platform
version: 1.1.0
date: 2026-04-26
status: Active
platform: github-actions
workflow: create-pipeline-scripts
---

# CI/CD Pipeline Specification

## Platform Summary

| Component | Platform | Purpose |
|-----------|----------|---------|
| CI/CD Automation | GitHub Actions | Workflow orchestration |
| Database | Supabase (supabase.com) | Managed PostgreSQL per environment |
| Backend API | Railway (railway.com) | .NET 9 API hosting per environment |
| Frontend SPA | InfinityFree (infinityfree.com) | React static files via FTP per environment |
| Container Registry | N/A | No Docker registry -- Railway builds from source |
| Secrets | GitHub Actions Secrets | All credentials stored encrypted |

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Backend | .NET / ASP.NET Core | 9.0 LTS |
| Frontend | React + Vite + TypeScript | Node 20 LTS |
| Database | PostgreSQL (via Supabase) | 16 |
| Cache | Redis (Railway add-on or Upstash) | 7 |
| CI Runner | ubuntu-latest | GitHub-hosted |

## Environment Matrix

| Environment | Branch/Trigger | API Host | DB | Frontend |
|-------------|---------------|----------|----|----------|
| dev | push to `develop` | Railway dev env | Supabase dev project | InfinityFree dev path |
| qa | after dev succeeds | Railway qa env | Supabase qa project | InfinityFree qa path |
| staging | push to `main` + approval | Railway staging env | Supabase staging project | InfinityFree staging path |
| production | tag `v*.*.*` + approval | Railway prod env | Supabase prod project | InfinityFree prod path |

## Workflow Map

| File | Purpose | Trigger | Environments |
|------|---------|---------|--------------|
| `ci.yml` | Build, lint, unit tests, E2E, PITR smoke, CodeQL, Gitleaks | push feature/develop/main, PR | ephemeral (CI only) |
| `cd-dev.yml` | Deploy to dev | push to `develop` | dev |
| `cd-qa.yml` | Deploy to QA | after dev workflow completes | qa |
| `cd-staging.yml` | Deploy to staging (approval gate) | push to `main` | staging |
| `cd-prod.yml` | Deploy to production (manual approval, canary) | tag `v*.*.*` | production |
| `security-scan.yml` | SAST, SCA, container scan, secrets, dep-review | push main/develop + weekly | N/A |

## Requirements

### Build (CICD-001--009)

- CICD-001: Build .NET 9 solution (`PropelIQ-Stub-Copilot.sln`) in Release configuration
- CICD-002: Build React SPA with `npm run build` in `client/`
- CICD-003: Railway deployment from source -- no Dockerfile required (uses Nixpacks/buildpacks)
- CICD-004: `dotnet tool restore` runs before `dotnet ef database update`
- CICD-005: `VITE_API_BASE_URL` injected at build time from GitHub secret per environment

### Quality (CICD-010--019)

- CICD-010: `dotnet format --verify-no-changes` on push
- CICD-011: ESLint on `client/src/` on push
- CICD-012: All lint failures block merge (exit-code non-zero)

### Security (CICD-020--029)

- CICD-020: CodeQL SAST (C#, JavaScript) on push and weekly schedule
- CICD-021: Gitleaks secrets detection with `fetch-depth: 0`
- CICD-022: `dotnet list package --vulnerable` + `npm audit --audit-level=high` (SCA)
- CICD-023: Trivy container scan if Dockerfile exists
- CICD-024: All credentials via `${{ secrets.NAME }}` -- never hardcoded
- CICD-025: Minimum required `permissions:` per workflow -- never `write-all`
- CICD-026: Snyk optional (`continue-on-error: true` if `SNYK_TOKEN` absent)

### Test (CICD-030--039)

- CICD-030: API unit tests use ephemeral GitHub Actions service containers (PostgreSQL 16, Redis 7) -- NEVER Supabase
- CICD-031: E2E Playwright smoke tests in `e2e/tests/smoke/`
- CICD-032: JUnit XML test artifacts uploaded with `if: always()`
- CICD-033: p95 load baseline < 2000ms (LoadBaselineTests.cs)
- CICD-034: PITR smoke test using `scripts/ci-pitr-restore-test.sh`

### Deployment (CICD-050--059)

- CICD-050: Backend deploys via `railway up --detach --environment <env> --service api`
- CICD-051: EF Core migrations run via `dotnet ef database update` against Supabase connection string after Railway deploy
- CICD-052: Frontend deploys via `lftp` FTP mirror to InfinityFree (SPA with `.htaccess` rewrite rules)
- CICD-053: `VITE_API_BASE_URL` environment variable baked into React build per environment
- CICD-054: Health check `GET /api/health` after every deployment (--retry 6 --retry-delay 10)
- CICD-055: Staging deployment gated by GitHub Environment protection rule (required reviewer)
- CICD-056: Production deployment gated by GitHub Environment protection rule (required reviewer)
- CICD-057: Production uses canary pattern: deploy --> observe 5 min --> promote full
- CICD-058: `railway rollback` auto-triggered on deployment failure (staging + prod)
- CICD-059: Slack notification on staging/prod success and failure/rollback

### Approval (CICD-060--069)

- CICD-060: GitHub Environment `staging` -- configure required reviewers in repo Settings --> Environments
- CICD-061: GitHub Environment `production` -- configure required reviewers + deployment branch filter `main`
- CICD-062: GitHub Environment `dev` and `qa` -- no approval required (auto-deploy)

## Required GitHub Secrets

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
