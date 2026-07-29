# Design Reference - AI Care Orchestration Platform

## Document Control

| Field | Value |
|---|---|
| Artifact | Design Reference |
| Version | 1.0 |
| Date | 2026-07-29 |
| Source Spec | .propel/context/docs/spec.md |
| Scope | UI and conversation experience references for eGFR care-gap workflow |

## 1. Purpose

This document maps specification requirements and epics to concrete design references, expected screen assets, and implementation-ready UX details.

It is the canonical location for linking Figma frames and exported design images used by implementation teams.

## 2. Design Asset Policy

- All design assets are prototype-safe and synthetic-data only.
- Every UI-impacting epic has a dedicated design folder under .propel/context/Design.
- Figma links and image exports should be attached before implementation starts.
- Conversation UX references include intent-level copy and decision prompts to keep parity with screen flow.

## 3. Global Design Tokens (Initial Baseline)

| Token Group | Baseline Decision |
|---|---|
| Color role model | Semantic palette (Info, Success, Warning, Risk High) with AA contrast compliance |
| Typography | Readability-first hierarchy for clinical review tasks |
| Spacing system | 8px base rhythm for predictable scan patterns |
| Elevation | Minimal depth; emphasis through contrast and border cues |
| Motion | Subtle state transitions only for analysis and approval states |
| Accessibility | WCAG 2.2 AA target for focus order, keyboard access, and contrast |

## 4. Epic-to-Design Mapping

### EP-001 - Patient Insight and Analysis Intake

| Item | Value |
|---|---|
| Requirement mapping | FR-001, FR-002, FR-003, FR-004, UXR-001 |
| UI impact | Yes |
| Key screens | Dashboard Home, Patient Search, Patient Summary (Pre-analysis) |
| Conversation impact | Search and patient confirmation prompts |
| Figma reference | Pending |
| Local asset folder | .propel/context/Design/EP-001/ |
| Asset checklist | search-results.png, patient-summary-pre-analysis.png |

### EP-002 - Explainable Care-Gap Intelligence

| Item | Value |
|---|---|
| Requirement mapping | FR-005, FR-006, FR-007, FR-008, UXR-002 |
| UI impact | Yes |
| Key screens | Analysis Result, Care-Gap Detail, Guideline Basis Panel |
| Conversation impact | Recommendation summary and rationale prompts |
| Figma reference | Pending |
| Local asset folder | .propel/context/Design/EP-002/ |
| Asset checklist | analysis-result.png, care-gap-detail.png, guideline-panel.png |

### EP-003 - Human Approval Control Gate

| Item | Value |
|---|---|
| Requirement mapping | FR-009, FR-010, FR-011, UXR-003 |
| UI impact | Yes |
| Key screens | Approval Decision Modal, Rejection Confirmation, Decision Receipt |
| Conversation impact | Explicit approve/reject confirmation prompts |
| Figma reference | Pending |
| Local asset folder | .propel/context/Design/EP-003/ |
| Asset checklist | approval-modal.png, rejection-flow.png |

### EP-004 - Workflow Orchestration and Notifications

| Item | Value |
|---|---|
| Requirement mapping | FR-012, FR-013, FR-014, FR-015, UXR-004 |
| UI impact | Yes |
| Key screens | Task Board, Task Timeline, Escalation Indicator, Notification Preview |
| Conversation impact | Task summary, overdue escalation prompts |
| Figma reference | Pending |
| Local asset folder | .propel/context/Design/EP-004/ |
| Asset checklist | task-board.png, task-timeline.png, escalation-state.png |

### EP-005 - Admin Configurability and Runtime Adaptation

| Item | Value |
|---|---|
| Requirement mapping | FR-016, FR-017 |
| UI impact | Yes |
| Key screens | Rule Configuration, Workflow Mapping, Change Preview |
| Conversation impact | Optional admin command prompts |
| Figma reference | Pending |
| Local asset folder | .propel/context/Design/EP-005/ |
| Asset checklist | rule-editor.png, mapping-editor.png |

### EP-006 - Omnichannel Experience Parity

| Item | Value |
|---|---|
| Requirement mapping | FR-018, FR-019, UXR-005 |
| UI impact | Yes |
| Key screens | Channel Parity Validation Views |
| Conversation impact | Full journey command and response library |
| Figma reference | Pending |
| Local asset folder | .propel/context/Design/EP-006/ |
| Asset checklist | parity-matrix.png, conversation-script-table.png |

### EP-007 - Auditability, Safety, and Resilience

| Item | Value |
|---|---|
| Requirement mapping | FR-020, FR-021, FR-022, FR-023, UXR-006 |
| UI impact | Yes |
| Key screens | Audit Timeline, Mock Mode Banner, Prototype Disclosure Surfaces |
| Conversation impact | Safety disclaimer and fallback status prompts |
| Figma reference | Pending |
| Local asset folder | .propel/context/Design/EP-007/ |
| Asset checklist | audit-timeline.png, mock-mode-banner.png, disclosure.png |

## 5. Screen Inventory

| Screen ID | Screen Name | Primary Epic | Key States |
|---|---|---|---|
| SCR-001 | Dashboard Home | EP-001 | Default, Loading, No patient selected |
| SCR-002 | Patient Search | EP-001 | Empty, Results, No results |
| SCR-003 | Patient Summary | EP-001 | Pre-analysis, Data unavailable |
| SCR-004 | Analysis Result | EP-002 | High risk, Medium risk, Low risk |
| SCR-005 | Care-Gap Detail | EP-002 | Validated, Flagged for review |
| SCR-006 | Approval Gate | EP-003 | Pending approval, Approved, Rejected |
| SCR-007 | Task Board | EP-004 | Created, In progress, Escalated, Completed |
| SCR-008 | Task Timeline | EP-004 | Event history, Escalation event |
| SCR-009 | Rule Configuration | EP-005 | Draft change, Validated change, Applied change |
| SCR-010 | Audit and Safety View | EP-007 | Normal mode, Mock mode, Disclosure visible |

## 6. Conversation UX References

| Conversation Step | Matching Screen Context | Required Copy Intent |
|---|---|---|
| Patient search prompt | SCR-002 | Confirm identity criteria and selected patient |
| Analysis trigger prompt | SCR-003 | Explicit action to start analysis |
| Recommendation explanation | SCR-004, SCR-005 | Risk, gaps, rationale, guideline basis |
| Approval gate prompt | SCR-006 | Explicit approve/reject with consequence warning |
| Task tracking prompt | SCR-007, SCR-008 | Current owner, due date, overdue status |
| Safety disclosure prompt | SCR-010 | Prototype-only and non-clinical-use statement |

## 7. Accessibility and Safety Design Checklist

- Keyboard navigable search, analysis, approval, and task flows.
- Focus trap and return-focus behavior in approval modal/dialog.
- Color usage for risk and escalation paired with text labels.
- Persistent prototype disclosure in analysis and approval surfaces.
- Readable typography and spacing for high-density clinical content.

## 8. Implementation Readiness

| Item | Status | Notes |
|---|---|---|
| Epic design mapping | Complete | Mapped all UI-impacting epics |
| Screen inventory | Complete | Core workflow surfaces enumerated |
| Local asset directories | Complete | Created EP-001 through EP-007 folders |
| Figma links attached | Pending | Add links when design file is available |
| Exported image assets attached | Pending | Add listed files in each EP folder |

## 9. Next Design Inputs Required

1. Figma project URL and frame IDs for each SCR item.
2. Finalized color, type, and spacing tokens from design lead.
3. Conversation copy deck for Dialogflow CX intents and confirmations.
4. Accessibility verification screenshots for keyboard/focus/contrast checks.
