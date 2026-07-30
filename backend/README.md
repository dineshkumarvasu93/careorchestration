# Backend Service Skeleton

This folder contains the US-001 FastAPI foundation for care orchestration.

## Endpoints

- `GET /health`: service liveness with status, service name, and version.
- `GET /ready`: startup readiness and registered orchestration routes.
- `GET /api/v1/orchestration/ping`: orchestration router reachability check.
- `GET /api/v1/orchestration/routes`: discoverable orchestration routes.
- `GET /api/v1/orchestration/rules/versions`: list published rule versions and active version.
- `GET /api/v1/orchestration/rules/active`: get active rule set.
- `POST /api/v1/orchestration/rules/publish`: publish a new validated rule version.
- `POST /api/v1/orchestration/rules/activate`: activate a published rule version.
- `GET /api/v1/orchestration/taxonomy/versions`: list published care-gap taxonomy versions.
- `GET /api/v1/orchestration/taxonomy/active`: get active taxonomy version and schema.
- `POST /api/v1/orchestration/taxonomy/publish`: publish a new taxonomy with compatibility metadata.
- `POST /api/v1/orchestration/taxonomy/activate`: activate published taxonomy version.
- `POST /api/v1/orchestration/taxonomy/validate`: validate gap payload against taxonomy schema.
- `POST /api/v1/orchestration/taxonomy/compatibility/check`: evaluate migration compatibility between versions.
- `GET /api/v1/orchestration/conversation/start`: starts conversation channel session with mandatory prototype disclaimer.
- `POST /api/v1/orchestration/cx/webhook`: Dialogflow CX webhook for search -> analyze -> review -> decision -> confirm journey.
- `POST /api/v1/orchestration/runs`: creates an orchestration run in `awaiting_approval` state.
- `GET /api/v1/orchestration/runs/{run_id}`: gets orchestration run status and decision state.
- `POST /api/v1/orchestration/runs/{run_id}/decision`: submit explicit `approve` or `reject` decision.
- `POST /api/v1/orchestration/runs/{run_id}/tasks/generate`: hard-guarded downstream task creation (approval required).
- `GET /api/v1/orchestration/runs/{run_id}/tasks`: lists generated tasks for a run.
- `POST /api/v1/orchestration/runs/{run_id}/tasks/{task_id}/status`: lifecycle status transition endpoint.
- `POST /api/v1/orchestration/runs/{run_id}/escalation/check`: scheduler-style overdue check and escalation emission.
- `GET /api/v1/orchestration/runs/{run_id}/timeline`: query append-only run event timeline.
- `GET /api/v1/orchestration/runs/{run_id}/tracking`: workflow tracking snapshot with status and escalation markers.
- `GET /api/v1/orchestration/analytics`: approval, conversion, and latency analytics summary for dashboard widgets.
- `POST /api/v1/orchestration/analysis/trigger`: explicit on-demand patient analysis trigger.
- `GET /api/v1/orchestration/analysis`: query persisted analysis results (optionally by patient).
- `GET /api/v1/orchestration/analysis/{analysis_id}`: get persisted analysis result by ID.
- `POST /api/v1/orchestration/analysis/{analysis_id}/validate`: classify recommendations with rule engine.
- `GET /api/v1/orchestration/analysis/{analysis_id}/validation`: fetch persisted validation decisions.
- `GET /api/v1/patients?query=...`: synthetic patient search (match/no-match supported).
- `GET /api/v1/patients/{patient_id}/profile`: unified CKD profile payload.
- `POST /api/v1/patients/ingest`: synthetic-only ingestion policy enforcement (`mode=reject|quarantine`).
- `GET /api/v1/policy/disclaimer`: channel-scoped disclaimer payload.
- `GET /api/v1/policy/audit/events`: recent synthetic-policy and disclaimer audit events.
- `GET /api/v1/policy/audit/integrity`: validates append-only audit hash-chain integrity.
- `GET /api/v1/policy/audit/patients/{patient_id}`: reconstructs patient timeline from linked audit events.

## Correlation ID and Request Logs

- Middleware reads `X-Correlation-ID` from incoming requests.
- If missing, middleware generates a UUID correlation ID.
- Response always includes the effective `X-Correlation-ID` header.
- Logs include structured request fields:
   - `correlation_id`
   - `method`
   - `route`
   - `status`
   - `latency_ms`

## Local Run

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start the API:
   - `uvicorn app.main:app --reload`

## Environment Variables

- `SERVICE_NAME` (default: `care-orchestration-api`)
- `APP_VERSION` (default: `0.1.0`)
- `APP_ENV` (allowed: `dev`, `test`, `prod`; default: `dev`)
- `API_PREFIX` (default: `/api/v1`)
- `ANALYSIS_MODE` (`mock` or `live`; default: `mock`)
- `GUIDELINE_SERVICE_URL` (required for healthy live guideline context path)
- `AI_SERVICE_URL` (required for healthy live recommendation path)

Invalid values produce actionable startup errors in logs.

## Synthetic Fixture Seed Data

- Fixture file: `app/data/fixtures/patients.json`
- Loader: `app/data/store.py`
- Startup behavior:
   - Validates required DR-001 fields.
   - Enforces `is_synthetic = true` for all records.
   - Quarantines nonconforming records and logs policy actions.
   - Loads in-memory store idempotently (replace-by-snapshot strategy).

## Synthetic-Only Policy and Disclaimers

- Shared disclaimer string is returned by patient/policy/conversation endpoints.
- Ingestion policy rejects or quarantines nonconforming records based on `mode`.
- Policy events are logged to in-memory audit with UTC timestamps and action metadata.

## Approval Gate (US-007)

- New runs start with `decision = pending` and `status = awaiting_approval`.
- `tasks/generate` is blocked with HTTP 409 until explicit approval.
- `reject` sets `status = rejected`, `terminated = true`, and permanently blocks task generation.
- All approval/rejection/task-generation gate events are appended to audit log.

## Immutable Decision Timeline (US-008)

- Decision submissions create immutable `decision_recorded` timeline events with actor, outcome, rationale, and timestamp.
- A second decision submission for the same run is rejected with HTTP 409 to enforce append-only semantics.
- Timeline is queryable using `GET /api/v1/orchestration/runs/{run_id}/timeline`.

## On-Demand Analysis (US-005)

- Analysis executes only when `POST /api/v1/orchestration/analysis/trigger` is called.
- Trigger builds profile + guideline context and runs deterministic AI adapter mapping (`TR-003`) to produce risk, gaps, reasoning, evidence, and confidence.
- Analysis output is persisted with `analysis_id` and linked `run_id` for later retrieval.

## Rule Validation and Review Routing (US-006)

- Rule evaluation classifies each recommendation as `valid`, `flagged`, or `needs_review`.
- Unknown gap vocabulary is `flagged` and blocked from auto-action (`auto_action_allowed = false`).
- Recommendations below confidence threshold are routed to `needs_review`.
- Validation decisions are persisted and attached to analysis/run records.
- Analysis-linked runs require validation before task generation and are blocked if review is required.

## Gap-To-Task Mapping (US-009)

- Approved recommendations are deterministically mapped to owner-specific task templates.
- Each created task contains `originating_gap_id`, `recommendation_id`, and `template_id`.
- If any recommendation is missing a template mapping, generation is blocked with HTTP 409.
- Missing mapping events are flagged in run timeline and audit log; no orphan tasks are created.

## Notification Dispatch with Retry (US-010)

- On task generation, notification dispatch is triggered for owners and patient.
- Retry policy is configurable using env vars (`NOTIFICATION_MAX_RETRIES`, `NOTIFICATION_BACKOFF_MS`) or per-request override in `POST /api/v1/orchestration/runs/{run_id}/tasks/generate`.
- Response includes notification delivery report with per-recipient attempt logs.
- Failure outcomes are logged with final status (`sent` or `failed`) and retry attempt details.

## Task Lifecycle and Escalation Tracking (US-011)

- Task lifecycle transitions are validated against allowed state flow and timestamped in per-task history.
- Overdue checks emit escalation events and mark tasks with escalation indicators.
- Tracking snapshots aggregate status counts, current statuses, and escalation markers for UI consumption.
- Tracking UI artifacts are in frontend/us011/workflow-tracking.html and frontend/us011/workflow-tracking.js.

## Dialogflow CX Webhook Journey (US-012)

- Webhook action flow supports `search`, `analyze`, `review`, `decision`, and `confirm`.
- Conversation flow reuses the same orchestration state and business logic as UI endpoints.
- Session context preserves patient, analysis, run, and decision state end-to-end.
- Approve path confirms by generating tasks; reject path confirms termination with zero task creation.

## Cross-Channel Parity Verification (US-013)

- Parity tests compare UI/API path against CX webhook path for identical fixtures and decisions.
- Suite validates risk and gap signatures are equal across channels.
- Suite validates task mapping outcomes (originating gap, template, owner) are equal across channels.
- Any mismatch causes test failure and should fail the release gate.

## Mock/Live Adapter and Deterministic Fallback (US-015)

- `ANALYSIS_MODE=mock` uses deterministic fixture-driven adapters.
- For patient `PT-0001` (John Smith), mock analysis returns `high` risk with three deterministic gaps.
- `ANALYSIS_MODE=live` attempts external guideline and AI adapters only when both health checks pass.
- Live-path failures or unhealthy dependencies fall back to deterministic mock mode.

## Offline Rehearsal and Outage Readiness (US-015 EP-008-II)

- Offline dependency rehearsal validates full coordinator flow (`analyze -> validate -> approve -> tasks`) with fallback to mock mode.
- Rehearsal evidence script: `backend/scripts/offline_rehearsal_evidence.py` collects latency and outage evidence artifacts.
- Recovery validation confirms switching from offline fallback back to healthy live mode without redeploy.

## Tamper-Evident Audit History (US-014)

- Audit events are append-only with deterministic `payload_hash` and `previous_hash -> current_hash` linkage.
- Each event captures `actor`, `action`, `timestamp_utc`, `channel`, and run/patient correlation where available.
- Integrity checks are exposed through `GET /api/v1/policy/audit/integrity`.
- Patient timeline reconstruction is exposed through `GET /api/v1/policy/audit/patients/{patient_id}`.

## Analytics Endpoints and Dashboard Widgets (US-018)

- Analytics API returns approval and conversion metrics plus latency aggregates.
- `widgets` payload returns canonical labels and values for dashboard rendering consistency.
- Frontend dashboard uses the same labels returned by the API to avoid drift.

## Rule Configuration Versioning (US-017)

- Rule configuration supports publish and activate lifecycle with server-side validation.
- Invalid rule publish payloads are rejected with HTTP 400.
- Active version is applied to the next analysis execution without redeploy.
- Version metadata is returned in analysis (`rule_version`) and rule validation payloads.

## Taxonomy Schema and Compatibility (US-019)

- Care-gap payloads are validated against active taxonomy schema required fields and severity contract.
- Nonconforming payloads return explicit validation errors through taxonomy validation endpoint.
- Version registry stores compatibility metadata (`compatible_from`, `migration_policy`).
- Compatibility checks support migration scenario testing between source and target taxonomy versions.

## Cross-Cutting Governance and Resilience (US-CROSS)

- E2E automation validates happy path and no-task-without-approval negative path enforcement.
- Privileged actions enforce role checks (`coordinator`/`admin` or `scheduler` for escalation checks).
- Authorization denials return HTTP 403 and emit audited `authorization` events.
- Live-mode offline dependency scenarios fall back to mock mode with latency budget assertion for demo resilience.
