from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unauthorized_decision_is_denied_and_audited() -> None:
    create_response = client.post(
        "/api/v1/orchestration/runs",
        json={
            "patient_id": "PT-0001",
            "recommendations": [
                {"gap_id": "GAP-UACR-MISSING", "recommendation_id": "REC-UACR-001", "title": "Order UACR"}
            ],
        },
    )
    assert create_response.status_code == 200
    run_id = create_response.json()["run"]["run_id"]

    deny_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={
            "decision": "approve",
            "actor": "viewer-user",
            "role": "viewer",
            "rationale": "Attempt unauthorized action",
        },
    )
    assert deny_response.status_code == 403
    assert "forbidden" in deny_response.json()["detail"]

    audit_response = client.get("/api/v1/policy/audit/events", params={"limit": 200})
    assert audit_response.status_code == 200
    events = audit_response.json()["events"]

    deny_events = [
        event
        for event in events
        if event.get("event_type") == "authorization"
        and event.get("action") == "denied"
        and event.get("details", {}).get("requested_action") == "decision_submit"
    ]
    assert deny_events


def test_unauthorized_rules_publish_is_denied_and_authorized_admin_is_allowed() -> None:
    version = f"RULES-RBAC-{uuid4()}"
    payload = {
        "version": version,
        "description": "RBAC publish test",
        "egfr_decline_threshold": 8,
        "uacr_missing_confidence": 0.92,
        "egfr_decline_confidence": 0.88,
        "high_risk_plan_confidence": 0.9,
        "include_high_risk_plan": True,
        "known_gap_ids": [
            "GAP-UACR-MISSING",
            "GAP-EGFR-DECLINE",
            "GAP-CKD-HIGH-RISK-PLAN",
            "GAP-NO-ACTION",
        ],
    }

    deny_response = client.post(
        "/api/v1/orchestration/rules/publish",
        json={**payload, "actor": "viewer-user", "role": "viewer"},
    )
    assert deny_response.status_code == 403

    allow_response = client.post(
        "/api/v1/orchestration/rules/publish",
        json={**payload, "actor": "admin-user", "role": "admin"},
    )
    assert allow_response.status_code == 200
    assert allow_response.json()["published"]["version"] == version
