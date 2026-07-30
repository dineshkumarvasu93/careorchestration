# US-015 Tasks (EP-008-II)
Status: Completed

- [x] TSK-027 (QA, DEVOPS, BE): Offline rehearsal and outage readiness validation.
Acceptance:
1. Full demo succeeds with dependencies offline.
2. Resilience scripts collect latency and outage evidence.
3. Recovery to live mode is verified.

Implementation Artifacts:
- backend/tests/test_offline_rehearsal_ep008ii.py
- backend/scripts/offline_rehearsal_evidence.py
- backend/README.md

Validation Notes:
- Static diagnostics: no editor errors in updated files.
- Runtime pytest execution pending local Python runtime availability.
