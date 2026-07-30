---
title: User Stories - AI Care Orchestration Platform (eGFR)
version: 1.1.0
date: 2026-07-29
status: Draft
source: .propel/context/docs/spec.md, .propel/context/docs/epics.md
workflow: create-user-stories
---

# User Story Backlog

## Objective

Define INVEST-compliant user stories with acceptance criteria and effort estimation for the eGFR care-gap orchestration platform.

## Estimation Model

- Story points: Fibonacci scale (1, 2, 3, 5, 8, 13).
- T-shirt size mapping: XS(1), S(2-3), M(5), L(8), XL(13).
- Priority scale:
  - P0: Required for demo-safe baseline.
  - P1: Strongly recommended for demo strength.
  - P2: Stretch.

## Story Summary

| Story ID | Canonical Epic | Execution Alias Epic | Story Title | Priority | Story Points | Size |
|---|---|---|---|---|---:|---|
| US-001 | EP-TECH | EP-TECH | Establish FastAPI orchestration skeleton and health contracts | P0 | 3 | S |
| US-002 | EP-TECH | EP-TECH | Implement correlation ID propagation and request tracing | P0 | 3 | S |
| US-003 | EP-001 | EP-DATA-I | Search patient and open unified CKD profile | P0 | 5 | M |
| US-004 | EP-001 | EP-DATA-I | Display raw CKD data before analysis | P0 | 3 | S |
| US-005 | EP-002 | EP-002 | Trigger guideline-grounded AI analysis on demand | P0 | 5 | M |
| US-006 | EP-002 | EP-002 | Validate recommendations against configurable rules | P0 | 5 | M |
| US-007 | EP-003 | EP-003 | Enforce explicit approval gate before task creation | P0 | 8 | L |
| US-008 | EP-003 | EP-003 | Record approval and rejection decisions with audit metadata | P0 | 3 | S |
| US-009 | EP-004 | EP-004 | Map approved care gaps to owner-specific tasks | P0 | 5 | M |
| US-010 | EP-004 | EP-004 | Notify owners and patient when tasks are created | P0 | 5 | M |
| US-011 | EP-004 | EP-004 | Track task lifecycle and escalate overdue tasks | P0 | 8 | L |
| US-012 | EP-006 | EP-006-I | Complete full coordinator journey via Dialogflow CX | P0 | 8 | L |
| US-013 | EP-006 | EP-006-II | Guarantee parity of outcomes between UI and conversation | P0 | 5 | M |
| US-014 | EP-007 | EP-007 | Persist append-only tamper-evident audit history | P0 | 8 | L |
| US-015 | EP-008 | EP-008-I, EP-008-II | Enable deterministic mock-mode fallback for external dependencies | P0 | 8 | L |
| US-016 | EP-007 | EP-DATA-I | Enforce synthetic-data-only policy and prototype disclaimers | P0 | 3 | S |
| US-017 | EP-005 | EP-005 | Allow clinical admin to edit and publish rule versions | P1 | 8 | L |
| US-018 | EP-009 | EP-009 | Expose analytics for approvals, task conversion, and SLA latency | P1 | 5 | M |
| US-019 | EP-010 | EP-DATA-II | Define and enforce canonical care-gap taxonomy contracts | P1 | 5 | M |

## Implementation Alias Notes

- Canonical epic IDs are the source of business traceability.
- Execution alias epic IDs are used for folder-level implementation planning under `.propel/context/tasks`.
- Story content and acceptance criteria are unchanged by aliasing.

## Detailed Stories

### US-001: Establish FastAPI orchestration skeleton and health contracts

- Canonical Epic: EP-TECH
- Execution Alias Epic: EP-TECH
- Priority: P0
- Story Points: 3 (S)
- User Story: As a platform engineer, I want a FastAPI orchestration skeleton with standard health contracts so that all channels can integrate consistently.
- Business Value: Enables reliable integration and delivery baseline.
- INVEST Check: Independent, Negotiable, Valuable, Estimable, Small, Testable.
- Acceptance Criteria:
  1. Given the service is deployed, when health endpoint is called, then API returns status and build version.
  2. Given API routes are initialized, when orchestration endpoints are queried, then documented contracts are discoverable.
  3. Given startup failures occur, when logs are reviewed, then failure reason is visible and actionable.
- Traceability: TR-001, NFR-001

### US-002: Implement correlation ID propagation and request tracing

- Canonical Epic: EP-TECH
- Execution Alias Epic: EP-TECH
- Priority: P0
- Story Points: 3 (S)
- User Story: As an operations engineer, I want correlation IDs propagated across requests so that end-to-end flows are traceable.
- Business Value: Reduces incident diagnosis time and supports accountability.
- INVEST Check: Independent, Valuable, Testable.
- Acceptance Criteria:
  1. Given a request includes a correlation ID, when it traverses APIs, then all logs include the same ID.
  2. Given a request omits correlation ID, when gateway receives it, then a new ID is generated and returned in response headers.
  3. Given UI and conversation requests execute equivalent actions, when logs are searched, then each chain is traceable by correlation ID.
- Traceability: NFR-009, TR-001

### US-003: Search patient and open unified CKD profile

- Canonical Epic: EP-001
- Execution Alias Epic: EP-DATA-I
- Priority: P0
- Story Points: 5 (M)
- User Story: As a care coordinator, I want to search and select a patient so that I can review the CKD context quickly.
- Business Value: Removes manual cross-referencing effort and improves speed.
- INVEST Check: Independent, Valuable, Estimable, Testable.
- Acceptance Criteria:
  1. Given valid search criteria, when the coordinator submits search, then matching synthetic patients are returned.
  2. Given a result is selected, when profile loads, then unified CKD profile is displayed.
  3. Given no matches exist, when search runs, then no-results state appears with retry option.
- Traceability: FR-001, DR-001, UC-001

### US-004: Display raw CKD data before analysis

- Canonical Epic: EP-001
- Execution Alias Epic: EP-DATA-I
- Priority: P0
- Story Points: 3 (S)
- User Story: As a care coordinator, I want raw CKD data shown before AI analysis so that I can independently verify baseline context.
- Business Value: Strengthens trust and reduces automation bias.
- INVEST Check: Small and testable presentation behavior.
- Acceptance Criteria:
  1. Given patient profile is opened, when no analysis is requested, then eGFR/UACR/visit fields are visible without AI outputs.
  2. Given analysis has not started, when viewing profile, then recommendation panel stays empty or clearly marked not analyzed.
  3. Given audit records are reviewed, when profile is viewed, then no analysis event exists until explicit trigger.
- Traceability: FR-002, UXR-001, UC-001

### US-005: Trigger guideline-grounded AI analysis on demand

- Canonical Epic: EP-002
- Execution Alias Epic: EP-002
- Priority: P0
- Story Points: 5 (M)
- User Story: As a care coordinator, I want to trigger analysis on demand so that recommendations are generated only when needed.
- Business Value: Maintains clinician control and context relevance.
- INVEST Check: Independent trigger behavior with measurable outcome.
- Acceptance Criteria:
  1. Given a patient is selected, when Analyze Patient is triggered, then system assembles patient context and requests guideline context.
  2. Given AI response is returned, when processing completes, then risk/gaps/recommendations are persisted in analysis result.
  3. Given no trigger occurs, when waiting on profile view, then no new analysis executes automatically.
- Traceability: FR-003, FR-004, TR-003, UC-002

### US-006: Validate recommendations against configurable rules

- Canonical Epic: EP-002
- Execution Alias Epic: EP-002
- Priority: P0
- Story Points: 5 (M)
- User Story: As a care coordinator, I want AI recommendations validated by hospital rules so that only policy-aligned actions are proposed.
- Business Value: Improves safety and local protocol alignment.
- INVEST Check: Valuable policy control; testable by rule fixtures.
- Acceptance Criteria:
  1. Given analysis recommendations exist, when rule engine runs, then each recommendation is classified valid or flagged.
  2. Given unrecognized gap vocabulary appears, when validation runs, then item is flagged and blocked from auto-action.
  3. Given low confidence threshold is breached, when validation completes, then item is routed to explicit human review state.
- Traceability: FR-007, FR-008, FR-009, TR-004, UC-002, UC-003

### US-007: Enforce explicit approval gate before task creation

- Canonical Epic: EP-003
- Execution Alias Epic: EP-003
- Priority: P0
- Story Points: 8 (L)
- User Story: As a care coordinator, I want explicit approve/reject controls so that no downstream tasks are created without my decision.
- Business Value: Delivers the core trust-first safety promise.
- INVEST Check: Central value with strict testability.
- Acceptance Criteria:
  1. Given recommendations are validated, when no approval decision is submitted, then task creation APIs reject orchestration requests.
  2. Given coordinator selects Approve, when decision is confirmed, then task generation is authorized.
  3. Given coordinator selects Reject, when decision is confirmed, then processing terminates with no tasks created.
  4. Given all completed runs are audited, when searching for tasks without approval, then count equals zero.
- Traceability: FR-010, FR-011, FR-012, UC-004

### US-008: Record approval and rejection decisions with audit metadata

- Canonical Epic: EP-003
- Execution Alias Epic: EP-003
- Priority: P0
- Story Points: 3 (S)
- User Story: As a compliance stakeholder, I want approval/rejection decisions recorded with actor metadata so that accountability is preserved.
- Business Value: Provides defensible decision trail.
- INVEST Check: Small, auditable, testable.
- Acceptance Criteria:
  1. Given coordinator submits decision, when save succeeds, then actor, timestamp, outcome, and rationale are stored.
  2. Given decision record exists, when patient history is reconstructed, then decision appears between analysis and task events.
  3. Given decision update attempts occur, when system receives modification request, then append-only semantics are enforced.
- Traceability: FR-021, DR-003, FR-023, UC-004

### US-009: Map approved care gaps to owner-specific tasks

- Canonical Epic: EP-004
- Execution Alias Epic: EP-004
- Priority: P0
- Story Points: 5 (M)
- User Story: As a workflow engine, I want each approved care gap mapped to task templates so that ownership is explicit.
- Business Value: Converts recommendations into action reliably.
- INVEST Check: Testable deterministic mapping.
- Acceptance Criteria:
  1. Given approved gap list exists, when orchestration runs, then each gap maps to a configured owner/task template.
  2. Given mapping succeeds, when tasks are created, then each task links to originating gap ID.
  3. Given mapping is missing, when orchestration runs, then issue is flagged and no orphan task is created.
- Traceability: FR-013, TR-005, DR-004, UC-005

### US-010: Notify owners and patient when tasks are created

- Canonical Epic: EP-004
- Execution Alias Epic: EP-004
- Priority: P0
- Story Points: 5 (M)
- User Story: As a care coordinator, I want owner and patient notifications sent on task creation so that follow-through begins immediately.
- Business Value: Improves execution speed and accountability.
- INVEST Check: Valuable and measurable delivery behavior.
- Acceptance Criteria:
  1. Given tasks are created, when notification workflow runs, then all required owners receive task alerts.
  2. Given tasks are created, when patient notification policy applies, then patient receives follow-up message.
  3. Given delivery fails, when retry policy executes, then retry attempts are logged with final outcome.
- Traceability: FR-015, TR-006, UC-005

### US-011: Track task lifecycle and escalate overdue tasks

- Canonical Epic: EP-004
- Execution Alias Epic: EP-004
- Priority: P0
- Story Points: 8 (L)
- User Story: As a care coordinator, I want task lifecycle tracking and overdue escalation so that care gaps are not left unresolved.
- Business Value: Ensures recommendations become completed work.
- INVEST Check: End-to-end operationally valuable and testable.
- Acceptance Criteria:
  1. Given tasks exist, when status changes occur, then lifecycle transitions are persisted and time-stamped.
  2. Given due time passes without completion, when scheduler runs, then escalation event is generated.
  3. Given workflow tracking view opens, when coordinator inspects run, then current status and escalation markers are visible.
- Traceability: FR-014, FR-016, DR-004, UC-008

### US-012: Complete full coordinator journey via Dialogflow CX

- Canonical Epic: EP-006
- Execution Alias Epic: EP-006-I
- Priority: P0
- Story Points: 8 (L)
- User Story: As a care coordinator, I want to run the entire process by conversation so that I can operate with low friction when screens are impractical.
- Business Value: Delivers channel flexibility without capability loss.
- INVEST Check: Valuable and testable by scripted conversation paths.
- Acceptance Criteria:
  1. Given authenticated session, when coordinator requests patient search in conversation, then assistant returns selectable patient context.
  2. Given patient selected, when coordinator requests analysis, then conversational channel triggers shared orchestration API.
  3. Given recommendations returned, when coordinator approves/rejects in conversation, then resulting workflow state is confirmed.
- Traceability: FR-019, TR-002, UC-007

### US-013: Guarantee parity of outcomes between UI and conversation

- Canonical Epic: EP-006
- Execution Alias Epic: EP-006-II
- Priority: P0
- Story Points: 5 (M)
- User Story: As a product owner, I want equivalent outcomes between UI and conversation for identical inputs so that trust and operations are consistent.
- Business Value: Prevents channel-dependent regressions.
- INVEST Check: Clear comparability and testability.
- Acceptance Criteria:
  1. Given the same patient fixture and decision path, when run via UI and conversation, then risk/gaps outputs match.
  2. Given same approval decision, when both channels execute, then generated tasks and owners match.
  3. Given parity test suite runs, when differences are detected, then release is blocked for parity defects.
- Traceability: FR-020, NFR-003, UXR-006, UC-007

### US-014: Persist append-only tamper-evident audit history

- Canonical Epic: EP-007
- Execution Alias Epic: EP-007
- Priority: P0
- Story Points: 8 (L)
- User Story: As an auditor, I want append-only, tamper-evident history so that every decision and action can be reconstructed confidently.
- Business Value: Supports defensibility and governance.
- INVEST Check: High value, bounded scope, deterministic tests.
- Acceptance Criteria:
  1. Given any state-changing action, when persisted, then an audit event is appended with actor, action, timestamp, payload hash, and channel.
  2. Given sequence of events, when integrity check runs, then hash linkage validates unchanged history.
  3. Given history query for patient, when requested, then full chain analysis to closure is reconstructable.
- Traceability: FR-021, FR-022, FR-023, TR-007, DR-005, UC-008

### US-015: Enable deterministic mock-mode fallback for external dependencies

- Canonical Epic: EP-008
- Execution Alias Epic: EP-008-I, EP-008-II
- Priority: P0
- Story Points: 8 (L)
- User Story: As a demo operator, I want deterministic mock-mode fallback so that the full demo works when external services are unavailable.
- Business Value: Protects demo reliability under dependency failure.
- INVEST Check: Critical reliability value with explicit test harness.
- Acceptance Criteria:
  1. Given mock mode is enabled, when AI/RAG/FHIR services are unreachable, then fixtures are served without flow breakage.
  2. Given John Smith fixture run, when analysis executes in mock mode, then expected three gaps and high risk are returned.
  3. Given mock mode disabled, when dependencies are healthy, then live integrations are used.
- Traceability: FR-025, NFR-004, NFR-010, TR-008, UC-002, UC-008

### US-016: Enforce synthetic-data-only policy and prototype disclaimers

- Canonical Epic: EP-007
- Execution Alias Epic: EP-DATA-I
- Priority: P0
- Story Points: 3 (S)
- User Story: As a governance lead, I want synthetic-only data enforcement and visible disclaimers so that prototype boundaries are explicit and safe.
- Business Value: Prevents compliance and safety violations.
- INVEST Check: Small policy and UX enforcement scope.
- Acceptance Criteria:
  1. Given data ingestion attempt, when record appears real-patient-like outside fixtures, then ingestion is rejected or quarantined.
  2. Given UI and conversation sessions, when coordinator starts workflow, then prototype/non-medical disclaimer is visible.
  3. Given audit reviews, when policy events occur, then policy enforcement actions are logged.
- Traceability: FR-024, FR-026, NFR-007, UXR-007

### US-017: Allow clinical admin to edit and publish rule versions

- Canonical Epic: EP-005
- Execution Alias Epic: EP-005
- Priority: P1
- Story Points: 8 (L)
- User Story: As a clinical admin, I want to edit and publish rule versions so that local care policy can adapt without redeployment.
- Business Value: Improves maintainability and local fit.
- INVEST Check: Negotiable UX details, clear value, testable rollout behavior.
- Acceptance Criteria:
  1. Given admin edits rule configuration, when validation passes, then version is publishable.
  2. Given version published, when next analysis runs, then new version is applied.
  3. Given invalid rule structure, when save is attempted, then actionable validation errors are shown.
- Traceability: FR-017, FR-018, DR-006, UC-006

### US-018: Expose analytics for approvals, task conversion, and SLA latency

- Canonical Epic: EP-009
- Execution Alias Epic: EP-009
- Priority: P1
- Story Points: 5 (M)
- User Story: As a product owner, I want analytics for approvals, conversion, and latency so that demo claims are measurable.
- Business Value: Quantifies value proposition and operational performance.
- INVEST Check: Measurable and testable with deterministic data.
- Acceptance Criteria:
  1. Given completed runs, when analytics endpoint is queried, then approval counts and rates are returned.
  2. Given approved gaps, when metrics are computed, then conversion-to-task percentages are available.
  3. Given run timing data, when queried, then analysis-to-task latency metrics are reported.
- Traceability: TR-009, NFR-002, FR-021

### US-019: Define and enforce canonical care-gap taxonomy contracts

- Canonical Epic: EP-010
- Execution Alias Epic: EP-DATA-II
- Priority: P1
- Story Points: 5 (M)
- User Story: As an integration lead, I want versioned care-gap taxonomy contracts so that cross-team payload compatibility is stable.
- Business Value: Prevents mapping failures and integration drift.
- INVEST Check: Clear contract boundary and automated validation.
- Acceptance Criteria:
  1. Given recommendation payloads, when validated, then gap types must match canonical taxonomy version.
  2. Given taxonomy update, when published, then backward compatibility policy is documented and enforced.
  3. Given nonconforming payload, when ingestion occurs, then request is rejected with explicit error.
- Traceability: TR-010, FR-007, FR-013, FR-020

## Sprint Suggestion (Hackathon)

| Sprint | Target Stories |
|---|---|
| Sprint 1 | US-001, US-002, US-003, US-004, US-005, US-006 |
| Sprint 2 | US-007, US-008, US-009, US-010, US-011 |
| Sprint 3 | US-012, US-013, US-014, US-015, US-016 |
| Sprint 4 | US-017, US-018, US-019 |

## Backlog Hygiene Rules

- Every story must map to at least one FR and one canonical epic.
- Execution alias mapping must be maintained for task-folder implementation planning.
- Acceptance criteria must be executable as tests.
- Stories above 8 points should be split before sprint commitment.
- P0 stories must be completed before P1/P2 unless dependency exception is approved.
