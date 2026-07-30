from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _valid_rules_payload(version: str, threshold: float = 8.0, include_high_risk_plan: bool = True) -> dict[str, object]:
    return {
        "version": version,
        "description": "Test published rules",
        "egfr_decline_threshold": threshold,
        "uacr_missing_confidence": 0.92,
        "egfr_decline_confidence": 0.88,
        "high_risk_plan_confidence": 0.9,
        "include_high_risk_plan": include_high_risk_plan,
        "known_gap_ids": [
            "GAP-UACR-MISSING",
            "GAP-EGFR-DECLINE",
            "GAP-CKD-HIGH-RISK-PLAN",
            "GAP-NO-ACTION",
        ],
    }


def _activate(version: str) -> None:
    response = client.post(
        "/api/v1/orchestration/rules/activate",
        json={"version": version, "actor": "qa"},
    )
    assert response.status_code == 200


def test_publish_validation_blocks_invalid_rules() -> None:
    invalid_payload = {
        "version": f"RULES-BAD-{uuid4()}",
        "description": "Invalid rule set",
        "egfr_decline_threshold": -1,
        "uacr_missing_confidence": 1.2,
        "egfr_decline_confidence": 0.7,
        "high_risk_plan_confidence": 0.7,
        "include_high_risk_plan": True,
        "known_gap_ids": ["GAP-UACR-MISSING"],
    }

    response = client.post("/api/v1/orchestration/rules/publish", json=invalid_payload)
    assert response.status_code == 400


def test_next_analysis_uses_active_version_without_redeploy() -> None:
    _activate("RULES-001")
    new_version = f"RULES-NEXT-{uuid4()}"

    publish_response = client.post(
        "/api/v1/orchestration/rules/publish",
        json=_valid_rules_payload(version=new_version, threshold=20.0, include_high_risk_plan=False),
    )
    assert publish_response.status_code == 200

    activate_response = client.post(
        "/api/v1/orchestration/rules/activate",
        json={"version": new_version, "actor": "qa"},
    )
    assert activate_response.status_code == 200

    try:
        analysis_response = client.post(
            "/api/v1/orchestration/analysis/trigger",
            json={"patient_id": "PT-0001"},
        )
        assert analysis_response.status_code == 200

        analysis = analysis_response.json()["analysis"]
        assert analysis["rule_version"] == new_version

        gap_ids = {gap["gap_id"] for gap in analysis["gaps"]}
        assert gap_ids == {"GAP-UACR-MISSING"}
    finally:
        _activate("RULES-001")


def test_version_behavior_change_is_test_verified() -> None:
    _activate("RULES-001")

    baseline_response = client.post(
        "/api/v1/orchestration/analysis/trigger",
        json={"patient_id": "PT-0001"},
    )
    assert baseline_response.status_code == 200
    baseline_analysis = baseline_response.json()["analysis"]
    baseline_gap_ids = {gap["gap_id"] for gap in baseline_analysis["gaps"]}

    new_version = f"RULES-BEHAVIOR-{uuid4()}"
    publish_response = client.post(
        "/api/v1/orchestration/rules/publish",
        json=_valid_rules_payload(version=new_version, threshold=20.0, include_high_risk_plan=False),
    )
    assert publish_response.status_code == 200

    activate_response = client.post(
        "/api/v1/orchestration/rules/activate",
        json={"version": new_version, "actor": "qa"},
    )
    assert activate_response.status_code == 200

    try:
        changed_response = client.post(
            "/api/v1/orchestration/analysis/trigger",
            json={"patient_id": "PT-0001"},
        )
        assert changed_response.status_code == 200
        changed_analysis = changed_response.json()["analysis"]
        changed_gap_ids = {gap["gap_id"] for gap in changed_analysis["gaps"]}

        assert baseline_gap_ids != changed_gap_ids
        assert len(baseline_gap_ids) >= 3
        assert changed_gap_ids == {"GAP-UACR-MISSING"}
    finally:
        _activate("RULES-001")
