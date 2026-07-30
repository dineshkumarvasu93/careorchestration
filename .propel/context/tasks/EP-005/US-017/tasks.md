# US-017 Tasks
Status: Completed

- [x] TSK-020 (BE, DATA, FE): Rule configuration management and versioning.
- [x] TSK-021 (BE, QA): Apply active version on next analysis.
Acceptance:
1. Publish validation blocks invalid rules.
2. Next analysis picks active version without redeploy.
3. Version behavior change is test-verified.

Implementation Artifacts:
- backend/app/rule_config_store.py
- backend/app/api/orchestration.py
- backend/app/analysis_engine.py
- backend/app/rule_engine.py
- backend/app/main.py
- backend/tests/test_rule_config_versioning.py
- frontend/us017/rule-config-dashboard.html
- frontend/us017/rule-config-dashboard.css
- frontend/us017/rule-config-dashboard.js
- frontend/us017/tests/rule-config-dashboard.spec.ts
- backend/README.md

Validation Notes:
- Static diagnostics: no editor errors in updated files.
- Runtime pytest execution pending local Python runtime availability.
- Runtime Playwright execution not run in this session.
