# US-016 Tasks
- [x] TSK-019 (SEC, FE, CX, BE): Synthetic-only policy and disclaimer enforcement.
Acceptance:
1. Nonconforming records are rejected or quarantined.
2. Disclaimer shown in UI and conversation.
3. Policy actions are audited.

Implementation Artifacts:
- backend/app/policy.py
- backend/app/api/policy.py
- backend/app/api/patients.py
- backend/app/api/orchestration.py
- backend/app/data/store.py
- backend/app/main.py
- backend/README.md
- frontend/us004/raw-ckd-profile.html
- frontend/us004/raw-ckd-profile.css
- frontend/us004/tests/raw-ckd-profile.spec.ts

Validation Notes:
- Static diagnostics: no editor errors in changed files.
- Runtime API and Playwright execution pending local Python/Playwright setup.
