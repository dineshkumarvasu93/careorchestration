# US-004 Tasks
- [x] TSK-005 (FE, QA): Raw CKD profile screen before analysis.
Acceptance:
1. Raw eGFR/UACR/visit values visible.
2. Recommendation panel is not-analyzed before trigger.
3. UI test verifies no AI output before analysis.

Implementation Artifacts:
- frontend/us004/raw-ckd-profile.html
- frontend/us004/raw-ckd-profile.css
- frontend/us004/raw-ckd-profile.js
- frontend/us004/tests/raw-ckd-profile.spec.ts

Validation Notes:
- Static diagnostics: no editor errors in created files.
- Runtime execution of Playwright test is pending local environment setup.
