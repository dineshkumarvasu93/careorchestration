# US-005 Tasks
Status: Completed

- [x] TSK-006 (BE, DATA): On-demand analysis endpoint.
- [x] TSK-007 (BE, DATA): Guideline/AI adapters and TR-003 mapping.
Acceptance:
1. Analysis runs only on explicit trigger.
2. DR-002 analysis result is persisted.
3. Payload includes risk, gaps, reasoning, evidence, confidence.

Implementation Artifacts:
- backend/app/analysis_engine.py
- backend/app/orchestration_state.py
- backend/app/api/orchestration.py
- backend/app/main.py
- backend/tests/test_on_demand_analysis.py
- backend/README.md

Validation Notes:
- Static diagnostics: no editor errors in updated files.
- Runtime pytest/API execution pending local Python runtime availability.
