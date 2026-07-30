# US-015 Tasks (EP-008-I)
Status: Completed

- [x] TSK-018 (BE, DATA, DEVOPS, QA): Mock/live adapters and deterministic fallback.
Acceptance:
1. Mock mode serves deterministic fixtures.
2. John Smith run returns high risk and expected three gaps.
3. Live mode uses external services when healthy.

Implementation Artifacts:
- backend/app/analysis_engine.py
- backend/tests/test_analysis_adapters.py
- backend/README.md

Validation Notes:
- Static diagnostics: no editor errors in updated files.
- Runtime pytest execution pending local Python runtime availability.
