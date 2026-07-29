# Business Requirements Document

## AI Care Orchestration Platform — eGFR Care-Gap Detection & Workflow Orchestration

| | |
|---|---|
| **Document** | Business Requirements Document (BRD) |
| **Version** | 0.1 — Draft for kickoff review |
| **Use case** | CKD care-gap detection driven by eGFR |
| **Our scope** | Workflow application + Dialogflow CX care-coordinator experience |
| **Build target** | Low-code: FlutterFlow · Dialogflow CX · FastAPI |
| **Status** | For stakeholder sign-off |

> **Not a medical device.** This prototype must not be used for clinical decision-making. All patient data is synthetic. Every AI recommendation is gated by human approval before any clinical task is created.

---

## Contents

1. [Executive summary](#1-executive-summary)
2. [Business objectives](#2-business-objectives)
3. [Problem statement](#3-problem-statement)
4. [Project scope](#4-project-scope)
5. [Stakeholders](#5-stakeholders)
6. [Current vs. future state](#6-current-vs-future-state)
7. [Business process — the eGFR journey](#7-business-process--the-egfr-journey)
8. [Business requirements](#8-business-requirements)
9. [Success metrics](#9-success-metrics)
10. [Assumptions, dependencies & constraints](#10-assumptions-dependencies--constraints)
11. [Business risks](#11-business-risks)
12. [Out of scope](#12-out-of-scope)
13. [Sign-off](#13-sign-off)

---

## 1. Executive summary

Patients with chronic kidney disease (CKD) need regular monitoring — repeat eGFR tests, annual UACR labs, and timely nephrology follow-up. In practice these steps are missed: results drift, labs go unordered, and specialist visits lapse. Each missed step is a **care gap**, and care gaps drive avoidable disease progression.

This platform detects those gaps automatically. It analyses a patient's kidney data against clinical guidelines, surfaces the gaps to a Care Coordinator with plain-language reasoning, and — once the coordinator approves — generates and tracks the follow-up tasks through to completion.

The business value is not the AI. It is the **orchestration**: turning a clinical signal into coordinated, tracked, accountable action, with a human in control of every decision. This document defines what the business needs from that platform, focused on the two components our team owns: the workflow application and the conversational care-coordinator experience.

---

## 2. Business objectives

The platform exists to serve these objectives, in priority order.

| # | Objective | Why it matters |
|---|---|---|
| **BO-1** | Detect CKD care gaps earlier and more consistently than manual review | Missed monitoring drives avoidable progression to kidney failure |
| **BO-2** | Keep a human in control of every clinical decision | Trust, safety and accountability; AI recommends, a clinician decides |
| **BO-3** | Convert a detected gap into tracked, owned follow-up tasks | A recommendation with no follow-through changes nothing |
| **BO-4** | Ground every recommendation in clinical guidelines | Defensibility — the reasoning must trace to a source, not a black box |
| **BO-5** | Let non-technical staff configure the care logic | Hospitals differ; the rules must be editable without engineering |
| **BO-6** | Give coordinators a fast, low-friction way to act | Screen or conversation, whichever fits the moment |

---

## 3. Problem statement

**Today, CKD monitoring depends on clinicians remembering to check.** A Care Coordinator reviewing a patient must mentally cross-reference the latest eGFR against the previous one, recall whether a UACR was ordered, notice how long it has been since the last nephrology visit, and know the relevant guideline thresholds — for every patient, from memory, under time pressure.

The consequences:

- **Gaps go unnoticed.** A declining eGFR or an overdue lab is easy to miss in a busy list.
- **Action is inconsistent.** Whether a gap is caught depends on who is reviewing and how much time they have.
- **Follow-through is untracked.** Even when a gap is spotted, there is no system ensuring the resulting task is created, assigned, and completed.
- **The reasoning is invisible.** Decisions live in a clinician's head, leaving no auditable trail of why an action was or wasn't taken.

**The example that anchors this project:** patient John Smith, 58, CKD Stage 3. His eGFR has fallen from 58 to 48. His UACR is missing. His last nephrology visit was 16 months ago. Three clear care gaps — each individually easy to miss, and together a meaningful risk that current process does not reliably catch.

---

## 4. Project scope

### 4.1 What our team delivers

Our team owns two of the platform's six workstreams: the **workflow application** (the screens and the workflow/task logic behind them) and the **Dialogflow CX care-coordinator experience** (the same journey driven by conversation).

| In scope for us | Delivered as |
|---|---|
| Patient search, dashboard and analysis trigger | FlutterFlow screens |
| AI recommendation and care-gap review | FlutterFlow screens |
| Care-gap validation against configurable rules | FastAPI backend |
| **Human approval gate** | FastAPI backend + UI |
| Workflow generation and task engine | FastAPI backend |
| Notifications and workflow tracking | FastAPI backend |
| Analytics dashboard | FlutterFlow screens |
| Conversational care coordinator | Dialogflow CX agent → FastAPI webhooks |

---

## 5. Stakeholders

| Stakeholder | Interest in the platform | Role in this project |
|---|---|---|
| **Care Coordinator** | Primary user. Needs gaps surfaced and tasks tracked without manual cross-referencing | Approves recommendations; drives the workflow |
| **Nephrologist / Doctor** | Receives well-triaged referrals with context | Acts on referral and review tasks |
| **Lab Team** | Receives clear, actionable lab orders | Fulfils repeat-eGFR and UACR tasks |
| **Pharmacist** | Flagged for medication review when relevant | Handles medication-review tasks |
| **Hospital / Clinical Admin** | Needs the care logic to match local protocol | Configures care-gap rules and workflows |
| **Patient** | Benefits from timely monitoring and follow-up | Receives notifications; no system access |
| **AI / RAG / FHIR teams** | Provide the intelligence and data layers | Deliver the services we orchestrate |
| **Hackathon judges** | Assess low-code delivery and AI orchestration | Evaluate the end-to-end demo |

---

## 6. Current vs. future state

### Current state

- Patient data sits across multiple systems; a coordinator assembles the picture manually.
- Care gaps are caught inconsistently, depending on who reviews and how much time they have.
- No systematic link between spotting a gap and ensuring the follow-up happens.
- Clinical reasoning is undocumented and unauditable.

### Future state

- The platform assembles the patient picture and analyses it against guidelines on demand.
- Care gaps are surfaced consistently, with plain-language reasoning and a guideline basis.
- A coordinator approves once; the platform generates, assigns, notifies and tracks every task.
- Every decision — AI recommendation, human approval, task action — is recorded and traceable.

> **The pivotal change is the approval gate.** The platform never acts on its own. It does the tedious detection and coordination; the clinician keeps the decision. That division is what makes the future state both safer and faster than today.

---

## 7. Business process — the eGFR journey

The journey the platform supports, end to end. This is the process the demo walks through.

1. **Coordinator logs in** and lands on the dashboard.
2. **Searches for the patient** — John Smith.
3. **Reviews the patient dashboard** — demographics, CKD stage, current and previous eGFR, UACR status, medication, last visit. *Nothing is analysed yet.*
4. **Requests analysis** — clicks *Analyze Patient*.
5. **The platform assembles the clinical picture** from available patient data.
6. **The platform retrieves relevant CKD guidelines** to ground the analysis.
7. **The AI analyses** the patient against the guidelines and returns risk, care gaps and recommended actions.
8. **The platform validates** the recommendations against configurable business rules.
9. **The platform maps** each confirmed gap to a workflow.
10. **The coordinator reviews** the recommendation — risk level, reasoning, proposed actions.
11. **The coordinator approves or rejects.** *This is the gate.*
12. **On approval, tasks are created** with the right owners — Lab, Coordinator, Pharmacist.
13. **Notifications go out** to everyone with a task, and to the patient.
14. **The workflow is tracked** to completion, feeding the analytics view.

For John Smith, a correct run produces: **risk High**; gaps *declining eGFR, missing UACR, no nephrology follow-up*; and, on approval, tasks to repeat the eGFR, order the UACR, and schedule a nephrology visit.

---

## 8. Business requirements

Business-level requirements — *what the business needs the platform to do*, independent of how it is built. Priorities follow MoSCoW: **Must** the demo fails without it · **Should** materially weakens the case without it · **Could** planned to drop under pressure.

### 8.1 Patient insight

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-01** | Let a coordinator find a patient and see their full CKD picture in one place | Must |
| **BR-02** | Present that picture before any analysis, so the coordinator sees raw data first | Must |
| **BR-03** | Analyse a patient's kidney data on demand, not on a fixed schedule | Must |

### 8.2 Trustworthy recommendations

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-04** | Identify care gaps a busy clinician could plausibly miss | Must |
| **BR-05** | Explain every recommendation in plain language a coordinator can judge | Must |
| **BR-06** | Ground each recommendation in a clinical-guideline basis | Must |
| **BR-07** | Confirm each AI recommendation against the hospital's own rules before presenting it as actionable | Must |
| **BR-08** | Flag, rather than act on, anything the rules do not recognise | Must |
| **BR-09** | Route low-confidence analyses to explicit human review | Should |

### 8.3 Human control

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-10** | Require explicit human approval before creating any task | Must |
| **BR-11** | Create nothing and take no downstream action until that approval is given | Must |
| **BR-12** | Stop cleanly on rejection and record the decision | Must |

### 8.4 Coordinated follow-through

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-13** | Turn each approved gap into concrete tasks with the correct owner | Must |
| **BR-14** | Track every task from creation to completion | Must |
| **BR-15** | Notify each task owner, and the patient, when work is created | Must |
| **BR-16** | Escalate work that is not acted on in time | Should |

### 8.5 Configurability

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-17** | Let non-technical staff edit the care-gap rules and workflows | Should |
| **BR-18** | Apply a change to the next analysis with no software redeployment | Must |

### 8.6 Access and choice of channel

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-19** | Let a coordinator drive the whole journey by conversation as well as by screen | Must |
| **BR-20** | Produce identical outcomes whether the coordinator uses the screen or the conversation | Must |

### 8.7 Accountability

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-21** | Record every analysis, approval, rejection and task action | Must |
| **BR-22** | Reconstruct the full history for any patient: analysis, reasoning, decision, tasks, actions | Must |
| **BR-23** | Keep that record tamper-evident and append-only | Must |

### 8.8 Safety and data handling

| ID | The business needs the platform to… | Priority |
|---|---|---|
| **BR-24** | Use only synthetic patient data in the prototype | Must |
| **BR-25** | Remain fully demonstrable when the AI, guideline or data services are unavailable | Must |
| **BR-26** | Present itself clearly as a prototype, not a clinical decision-making tool | Must |

---

## 9. Success metrics

How the business will judge whether the platform delivers. Prototype targets are demo-scale; production targets show the intended direction.

| Metric | Ties to | Prototype target | Production direction |
|---|---|---|---|
| Care gaps detected per analysed patient | BO-1 | All three gaps found for the example patient | Match or exceed expert manual review |
| Recommendations with a visible guideline basis | BO-4 | 100% | 100% |
| Actions taken without human approval | BO-2 | **Zero** | **Zero** |
| Approved gaps that become tracked tasks | BO-3 | 100% | 100% |
| Rule change applied without redeployment | BO-5 | Demonstrated live | Self-service by admins |
| Journey completable by conversation | BO-6 | Full journey via Dialogflow CX | Parity with the UI |
| Time from analysis to task creation | BO-3 | Seconds in the demo | Faster than manual coordination |
| Full demo runs offline from mocks | BR-25 | Yes | N/A (resilience property) |

> The single most important number is **zero actions without approval**. It is the metric that expresses the platform's core promise, and the one a judge or a clinician will test first.

---

## 10. Assumptions, dependencies & constraints

### Assumptions

- The AI service returns structured risk, care gaps and recommendations.
- The RAG service returns relevant guideline sections for a patient.
- Mock patient data is acceptable for the prototype; no live clinical system is required.
- A single patient journey (the eGFR example) is sufficient to demonstrate the platform.
- Coordinators act inside our application, by screen or conversation.

### Dependencies

| Dependency | Owner | Needed by |
|---|---|---|
| Frozen AI-response and patient-data contract | All teams | Kickoff, before build |
| Guideline-retrieval service | RAG team | Analysis step |
| Mock patient dataset for the example patient | Our team | Analysis step |
| Reachable AI analysis service | AI team | Integration |
| A working notification channel | Our team | Notification step |

### Constraints

- **Timebox.** Hackathon delivery over short working days; scope is deliberately tight.
- **Low-code build target.** FlutterFlow, Dialogflow CX and FastAPI, to suit the judging emphasis.
- **No real patient data**, at any point.
- **No regulatory clearance**, so the prototype cannot be used clinically.

---

## 11. Business risks

| Risk | Business consequence | Response |
|---|---|---|
| The approval gate is weakened to save time | The platform's core safety promise is lost; the pitch fails its first test | BR-10/BR-11 are Must; the demo proves no task exists before approval |
| Recommendations aren't grounded in guidelines | Output looks like an unaccountable black box | BR-06 is Must; every recommendation shows its guideline basis |
| Configurability is faked with hardcoded rules | The "hospitals configure their own care logic" claim collapses | BR-17/BR-18 are Must; a rule is edited live during the demo |
| The conversation and the screen diverge | Coordinators get different outcomes through different channels | BR-20 is Must; both routes drive one shared backend |
| The care-gap vocabulary shifts after kickoff | Validation rules and workflow mapping break across teams | Freeze the vocabulary at kickoff as a joint decision |
| The demo depends on live external services | A network failure ends the pitch | BR-25 is Must; the platform runs from mocks behind a flag |
| Real patient data is used for convenience | A serious data-governance breach | BR-24 is Must; data is generated, never sourced |

---

## 12. Out of scope

Explicitly excluded from this project. If asked, these are production concerns deliberately deferred, not oversights.

- Model training, tuning and clinical accuracy — owned by the AI team.
- Building the guideline knowledge base and embeddings — owned by the RAG team.
- Live EHR, lab or pharmacy integration — simulated for the prototype.
- Real single sign-on — demo users only; enterprise identity is the production path.
- Real patient data of any kind.
- Multi-hospital tenancy — the architecture allows for it; it is not built.
- Clinical validation or regulatory certification.
- Native mobile applications — responsive web and conversation only.

---

## 13. Sign-off

Section 10 (Assumptions, dependencies & constraints) requires agreement from the AI, RAG and FHIR teams before development begins. The business requirements in section 8 are owned by our team and may be refined as long as the success metrics in section 9 still hold.

| Role | Name | Date | Approved |
|---|---|---|---|
| Product / business owner | | | |
| Workflow app lead | | | |
| Dialogflow CX owner | | | |
| AI model lead | | | |
| RAG team lead | | | |

---

*This is a hackathon prototype and not a medical device. It must not be used for clinical decision-making. All patient data is synthetic.*
