---
title: Epic Decomposition - AI Care Orchestration Platform (eGFR)
version: 1.0.0
date: 2026-07-29
status: Draft
source: .propel/context/docs/spec.md
workflow: create-epics
---

# Epic Decomposition

## Objective

Decompose the eGFR care-orchestration requirements into prioritized, actionable epics with clear traceability to FR, NFR, TR, DR, UXR, and UC identifiers.

## Prioritization Model

- P0: Mandatory for demo success and safety claims.
- P1: High-value capabilities that materially strengthen the demo.
- P2: Stretch capabilities if time remains.

## Epic Traceability Matrix

| Epic ID | Epic Name | Priority | Business Value Alignment | Requirement Mapping | Use Case Mapping |
|---|---|---|---|---|---|
| EP-TECH | Platform Foundation and Environment | P0 | Enables end-to-end delivery reliability | NFR-001, NFR-004, NFR-006, NFR-009, TR-001, TR-008 | UC-001 to UC-008 |
| EP-001 | Patient Context and Analysis Trigger | P0 | Reduces manual data hunting, starts orchestration flow | FR-001, FR-002, FR-003, DR-001, UXR-001 | UC-001, UC-002 |
| EP-002 | Guideline-Grounded Recommendation Engine | P0 | Improves consistency and defensibility of gap detection | FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, TR-003, TR-004, DR-002, UXR-002 | UC-002, UC-003 |
| EP-003 | Human Approval Gate and Decision Capture | P0 | Enforces trust-first safety promise and accountability | FR-010, FR-011, FR-012, FR-021, DR-003, UXR-003 | UC-004 |
| EP-004 | Workflow and Task Orchestration | P0 | Converts recommendations into owned and trackable action | FR-013, FR-014, FR-015, FR-016, TR-005, TR-006, DR-004, UXR-004 | UC-005, UC-008 |
| EP-005 | Configurable Care Logic | P1 | Enables hospital-specific adaptation without engineering bottlenecks | FR-017, FR-018, TR-004, DR-006 | UC-006 |
| EP-006 | Multi-Channel Coordinator Parity (UI + Conversation) | P0 | Supports low-friction operation choice with equivalent outcomes | FR-019, FR-020, NFR-003, TR-002, UXR-005, UXR-006 | UC-007 |
| EP-007 | Auditability, Safety Labels, and Synthetic Data Governance | P0 | Demonstrates safe prototype boundaries and full traceability | FR-022, FR-023, FR-024, FR-026, NFR-005, NFR-007, NFR-008, DR-005, DR-007, UXR-007 | UC-008 |
| EP-008 | Mock-Mode Resilience and Demo Continuity | P0 | Ensures full demonstrability despite dependency outages | FR-025, NFR-004, NFR-010, TR-008 | UC-002, UC-008 |
| EP-009 | Analytics and Operational Visibility | P1 | Provides measurable proof of value and operational control | TR-009, NFR-002, FR-014, FR-021 | UC-008 |
| EP-010 | Canonical Care-Gap Taxonomy and Contract Governance | P1 | Prevents cross-team drift and orchestration mismatch | TR-010, FR-007, FR-013, FR-020 | UC-002, UC-005, UC-007 |

## Implementation-Friendly Epic Partition (PropelIQ Task Tree)

To align with EP-folder execution under `.propel/context/tasks`, the following split can be used without changing business scope.

| Partition Epic ID | Derived From | Partition Focus | Story/Task Orientation |
|---|---|---|---|
| EP-006-I | EP-006 | Dialogflow CX journey execution via shared backend | US-012, TSK-015 |
| EP-006-II | EP-006 | Cross-channel outcome parity verification | US-013, TSK-016 |
| EP-008-I | EP-008 | Mock adapters and runtime fallback behavior | US-015, TSK-018 |
| EP-008-II | EP-008 | Offline demo rehearsal and outage readiness validation | US-015, TSK-018, TSK-027 |
| EP-DATA-I | EP-001/EP-007 | Synthetic fixture and seed-data governance baseline | US-003, US-004, US-016, TSK-003 |
| EP-DATA-II | EP-010 | Taxonomy versioning and compatibility enforcement | US-019, TSK-023, TSK-024 |

Notes:

- Canonical backlog IDs remain EP-001 to EP-010 plus EP-TECH.
- Partition IDs are execution aliases intended for folder-level planning and sprint tracking.

## Epic Details

### EP-TECH: Platform Foundation and Environment (P0)

- Purpose: Establish the shared backend and deployment foundation needed for reliable delivery.
- Scope:
  - FastAPI service skeleton and environment configuration.
  - Shared request/response envelopes with correlation ID propagation.
  - TLS and baseline access controls for coordinator/admin paths.
  - Mock-mode switch framework with deterministic fixture routing.
- Acceptance Highlights:
  - Base API health and orchestration endpoint contracts are reachable.
  - Correlation IDs propagate across requests and logs.
  - Mock-mode toggle enables deterministic responses without external dependencies.
- Dependencies: None.

### EP-001: Patient Context and Analysis Trigger (P0)

- Purpose: Provide the coordinator with raw CKD context and explicit analysis initiation.
- Scope:
  - Patient search and profile retrieval APIs.
  - UI and conversational raw-data presentation parity.
  - Analyze action initiation hooks.
- Acceptance Highlights:
  - Raw CKD data visible before any AI result.
  - Analysis starts only on explicit user trigger.
- Dependencies: EP-TECH.

### EP-002: Guideline-Grounded Recommendation Engine (P0)

- Purpose: Produce recommendations with visible reasoning and rule validation.
- Scope:
  - AI/RAG integration contract handling.
  - Recommendation normalization and confidence handling.
  - Rule validation and unrecognized-gap flagging.
- Acceptance Highlights:
  - Each recommendation includes risk, reasoning, guideline basis, and confidence.
  - Unknown gap types are flagged and blocked from auto-action.
- Dependencies: EP-TECH, EP-001.

### EP-003: Human Approval Gate and Decision Capture (P0)

- Purpose: Enforce explicit human decisioning before any action.
- Scope:
  - Approve/reject endpoints and UX controls.
  - Hard orchestration guard that blocks task creation pre-approval.
  - Decision event capture with actor and timestamp.
- Acceptance Highlights:
  - Zero tasks can exist before approval.
  - Rejection cleanly terminates downstream processing.
- Dependencies: EP-002.

### EP-004: Workflow and Task Orchestration (P0)

- Purpose: Convert approved recommendations into owned tasks and track completion.
- Scope:
  - Gap-to-task template mapping.
  - Task state machine lifecycle.
  - Owner and patient notification dispatch with retry logging.
  - Overdue escalation triggers.
- Acceptance Highlights:
  - All approved gaps produce mapped tasks with owners.
  - Task lifecycle is visible from creation to completion.
- Dependencies: EP-003.

### EP-005: Configurable Care Logic (P1)

- Purpose: Allow non-technical configuration of rules and mappings.
- Scope:
  - Rule and mapping configuration management.
  - Validation and publish flow with versioning.
  - Next-run application of published changes.
- Acceptance Highlights:
  - Configuration changes apply without service redeploy.
  - Invalid rules are rejected with actionable errors.
- Dependencies: EP-002, EP-004.

### EP-006: Multi-Channel Coordinator Parity (UI + Conversation) (P0)

- Purpose: Ensure equivalent outcomes from screen and conversational channels.
- Scope:
  - Dialogflow CX webhook fulfillment via shared orchestration APIs.
  - Intent-to-action mapping for full journey completion.
  - Cross-channel terminology and output consistency checks.
- Acceptance Highlights:
  - Same input data yields equivalent recommendation and task outputs across channels.
- Dependencies: EP-001, EP-002, EP-003, EP-004.

### EP-007: Auditability, Safety Labels, and Synthetic Data Governance (P0)

- Purpose: Protect safety claims and provide full decision/action traceability.
- Scope:
  - Append-only audit event persistence.
  - Safety disclaimer surfacing across channels.
  - Synthetic-data policy checks in fixtures and test data pipelines.
- Acceptance Highlights:
  - Full history reconstruction for a patient run is possible.
  - Prototype warning is always visible.
- Dependencies: EP-TECH, EP-003, EP-004.

### EP-008: Mock-Mode Resilience and Demo Continuity (P0)

- Purpose: Guarantee demo execution independent of external service availability.
- Scope:
  - Mock adapters for AI, guideline retrieval, and data dependencies.
  - Dependency outage detection and fallback behavior.
  - Demo scenario fixtures including the John Smith expected outcome set.
- Acceptance Highlights:
  - Full journey executes successfully with dependencies offline.
- Dependencies: EP-TECH, EP-001, EP-002, EP-004.

### EP-009: Analytics and Operational Visibility (P1)

- Purpose: Provide measurable outcomes and operational status visibility.
- Scope:
  - Dashboard metrics for approvals, tasks, overdue items, and conversion rates.
  - Latency and throughput telemetry for key orchestration steps.
- Acceptance Highlights:
  - Metrics prove core claims: zero unapproved actions and approved-gap conversion.
- Dependencies: EP-004, EP-007.

### EP-010: Canonical Care-Gap Taxonomy and Contract Governance (P1)

- Purpose: Keep teams aligned on gap vocabulary and payload contracts.
- Scope:
  - Versioned care-gap taxonomy artifact.
  - Contract governance process and backward compatibility guidance.
  - Validation checks for payload conformance.
- Acceptance Highlights:
  - All payloads conform to a versioned taxonomy and schema.
- Dependencies: EP-002, EP-004, EP-006.

## Delivery Waves

| Wave | Included Epics | Rationale |
|---|---|---|
| Wave 1 - Foundation | EP-TECH, EP-001, EP-002 | Establish data context and recommendation baseline |
| Wave 2 - Safety and Action | EP-003, EP-004, EP-007 | Deliver core trust promise and end-to-end orchestration |
| Wave 3 - Channel and Resilience | EP-006, EP-008 (or EP-006-I, EP-006-II, EP-008-I, EP-008-II) | Complete multi-channel and outage-proof demo requirements |
| Wave 4 - Optimization | EP-005, EP-009, EP-010 (plus EP-DATA-II where used) | Improve configurability, insights, and governance maturity |

## Critical Path

1. EP-TECH
2. EP-001
3. EP-002
4. EP-003
5. EP-004
6. EP-006
7. EP-008
8. EP-007

## Definition of Done for Epic Completion

- Mapped FR/UC items for the epic are demonstrably satisfied.
- Required audit evidence is emitted and queryable.
- Security and synthetic-data constraints are preserved.
- Mock-mode behavior remains intact for affected flows.
- No regression in approval-gate enforcement.

## Risks in Epic Execution

| Risk | Affected Epics | Mitigation |
|---|---|---|
| Approval gate implemented late | EP-003, EP-004 | Prioritize EP-003 in Wave 2 with explicit blocking tests |
| Channel divergence | EP-006 | Use shared backend APIs and parity test snapshots |
| Taxonomy drift across teams | EP-002, EP-010 | Freeze vocabulary and enforce schema checks |
| Demo outage from upstream dependency failure | EP-008 | Maintain deterministic fixtures and outage fallback tests |

## Suggested Initial Backlog Cut for Hackathon

- Must complete: EP-TECH, EP-001, EP-002, EP-003, EP-004, EP-006, EP-008, EP-007.
- Should complete: EP-005, EP-009.
- Could complete: EP-010.

Implementation alias view (optional for folder-level execution):

- Must complete: EP-TECH, EP-001, EP-002, EP-003, EP-004, EP-006-I, EP-006-II, EP-008-I, EP-008-II, EP-007, EP-DATA-I.
- Should complete: EP-005, EP-009.
- Could complete: EP-010, EP-DATA-II.
