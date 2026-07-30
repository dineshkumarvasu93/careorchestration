---
title: Development Task Plan - AI Care Orchestration Platform (eGFR)
version: 1.1.0
date: 2026-07-29
status: Draft
source: .propel/context/docs/user-stories.md
workflow: plan-development-tasks
---

# Development Task Plan

## Objective

Generate implementation tasks from user stories with acceptance criteria split by technology layer.

## Layer Model

- FE: FlutterFlow/Web UI
- BE: FastAPI orchestration and APIs
- CX: Dialogflow CX and webhook flow
- DATA: schemas, fixtures, persistence, contracts
- DEVOPS: runtime config, environment, scheduling
- QA: automated validation and regression
- SEC: RBAC, governance, audit integrity

## Task Summary

| Task ID | Story | Canonical Epic | Alias Epic | Layers |
|---|---|---|---|---|
| TSK-001 | US-001 | EP-TECH | EP-TECH | BE, DEVOPS |
| TSK-002 | US-002 | EP-TECH | EP-TECH | BE, DEVOPS |
| TSK-003 | US-003 | EP-001 | EP-DATA-I | DATA, BE, SEC |
| TSK-004 | US-003 | EP-001 | EP-DATA-I | BE, DATA, QA |
| TSK-005 | US-004 | EP-001 | EP-DATA-I | FE, QA |
| TSK-006 | US-005 | EP-002 | EP-002 | BE, DATA |
| TSK-007 | US-005 | EP-002 | EP-002 | BE, DATA |
| TSK-008 | US-006 | EP-002 | EP-002 | BE, DATA, QA |
| TSK-009 | US-007 | EP-003 | EP-003 | BE, SEC, QA |
| TSK-010 | US-008 | EP-003 | EP-003 | DATA, BE, SEC |
| TSK-011 | US-009 | EP-004 | EP-004 | BE, DATA |
| TSK-012 | US-011 | EP-004 | EP-004 | BE, DATA, DEVOPS |
| TSK-013 | US-010 | EP-004 | EP-004 | BE, DEVOPS, QA |
| TSK-014 | US-011 | EP-004 | EP-004 | FE, BE, QA |
| TSK-015 | US-012 | EP-006 | EP-006-I | CX, BE |
| TSK-016 | US-013 | EP-006 | EP-006-II | QA, FE, CX, BE |
| TSK-017 | US-014 | EP-007 | EP-007 | DATA, BE, SEC |
| TSK-018 | US-015 | EP-008 | EP-008-I | BE, DATA, DEVOPS, QA |
| TSK-019 | US-016 | EP-007 | EP-DATA-I | SEC, FE, CX, BE |
| TSK-020 | US-017 | EP-005 | EP-005 | BE, DATA, FE |
| TSK-021 | US-017 | EP-005 | EP-005 | BE, QA |
| TSK-022 | US-018 | EP-009 | EP-009 | BE, FE, DATA |
| TSK-023 | US-019 | EP-010 | EP-DATA-II | DATA, BE, QA |
| TSK-024 | US-019 | EP-010 | EP-DATA-II | BE, DATA, QA |
| TSK-025 | US-001-US-016 | Multiple | EP-CROSS | QA |
| TSK-026 | US-007, US-017 | EP-003, EP-005 | EP-CROSS | SEC, BE, QA |
| TSK-027 | US-015, US-018 | EP-008, EP-009 | EP-008-II, EP-CROSS | QA, DEVOPS, BE |

## Acceptance Breakdown by Layer

### FE

- Raw CKD profile renders before analysis trigger.
- Task tracking and escalation states are visible and accurate.
- Analytics widgets display approval, conversion, and latency metrics.
- Prototype safety disclaimer is visible in key coordinator moments.

### BE

- Analysis runs only on explicit trigger.
- Task creation is impossible without approval.
- Gap-to-task mapping is deterministic and auditable.
- Shared APIs are used by both UI and Dialogflow CX pathways.

### CX

- Conversation covers patient search, analysis trigger, review, decision, and confirmation.
- Conversation outputs match UI outcomes for equivalent inputs.
- Safety disclaimer is presented consistently in conversational flow.

### DATA

- Synthetic fixtures include DR-001 fields and John Smith scenario.
- Analysis output includes DR-002 payload contract fields.
- Audit records are append-only and hash-linked for tamper evidence.
- Taxonomy versions and compatibility metadata are persisted.

### DEVOPS

- Correlation ID and latency fields are logged for every request.
- Scheduler jobs are configurable for escalation checks.
- Mock/live mode switch is environment driven and deterministic.

### QA

- E2E tests cover happy path and no-approval negative path.
- Parity tests gate releases on channel divergence.
- Mock-mode offline execution passes for complete demo flow.

### SEC

- RBAC policies enforce coordinator/admin permissions.
- Synthetic-only data policy rejects or quarantines invalid records.
- Audit tamper attempts are blocked and logged.

## Sprint Mapping

- Sprint 1: TSK-001 to TSK-008
- Sprint 2: TSK-009 to TSK-014
- Sprint 3: TSK-015 to TSK-019
- Sprint 4: TSK-020 to TSK-024
- Cross-sprint: TSK-025 to TSK-027
