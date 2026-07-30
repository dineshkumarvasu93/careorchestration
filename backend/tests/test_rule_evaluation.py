from fastapi.testclient import TestClient

from app.main import app
from app.rule_engine import rule_evaluation_engine

client = TestClient(app)


def _trigger_analysis(patient_id: str = "PT-0001") -> dict[str, object]:
    response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": patient_id})
    assert response.status_code == 200
    return response.json()["analysis"]


def test_recommendations_classified_valid_flagged_needs_review() -> None:
    synthetic_analysis = {
        "gaps": [
            {
                "gap_id": "GAP-UACR-MISSING",
                "recommendation_id": "REC-1",
                "confidence": 0.95,
            },
            {
                "gap_id": "GAP-UNKNOWN-NEW",
                "recommendation_id": "REC-2",
                "confidence": 0.99,
            },
            {
                "gap_id": "GAP-EGFR-DECLINE",
                "recommendation_id": "REC-3",
                "confidence": 0.45,
            },
        ]
    }

    result = rule_evaluation_engine.evaluate(analysis=synthetic_analysis, confidence_threshold=0.8)
    classifications = [decision["classification"] for decision in result["decisions"]]

    assert "valid" in classifications
    assert "flagged" in classifications
    assert "needs_review" in classifications


def test_unknown_gaps_blocked_from_auto_action() -> None:
    synthetic_analysis = {
        "gaps": [
            {
                "gap_id": "GAP-UNKNOWN-NEW",
                "recommendation_id": "REC-UNLISTED",
                "confidence": 0.99,
            }
        ]
    }

    result = rule_evaluation_engine.evaluate(analysis=synthetic_analysis, confidence_threshold=0.8)
    decision = result["decisions"][0]

    assert decision["classification"] == "flagged"
    assert decision["auto_action_allowed"] is False
    assert decision["reason"] == "unknown_gap_vocabulary"


def test_rule_decisions_are_persisted_and_queryable() -> None:
    analysis = _trigger_analysis("PT-0001")
    analysis_id = str(analysis["analysis_id"])
    run_id = str(analysis["run_id"])

    validate_response = client.post(
        f"/api/v1/orchestration/analysis/{analysis_id}/validate",
        json={"confidence_threshold": 0.9, "actor": "rule-engine-qa"},
    )
    assert validate_response.status_code == 200

    persisted_response = client.get(f"/api/v1/orchestration/analysis/{analysis_id}/validation")
    assert persisted_response.status_code == 200
    validation = persisted_response.json()["validation"]

    assert validation["analysis_id"] == analysis_id
    assert validation["run_id"] == run_id
    assert validation["actor"] == "rule-engine-qa"
    assert isinstance(validation["decisions"], list)
    assert len(validation["decisions"]) >= 1


def test_low_confidence_routes_to_review_and_blocks_task_generation() -> None:
    analysis = _trigger_analysis("PT-0001")
    analysis_id = str(analysis["analysis_id"])
    run_id = str(analysis["run_id"])

    validate_response = client.post(
        f"/api/v1/orchestration/analysis/{analysis_id}/validate",
        json={"confidence_threshold": 0.99, "actor": "rule-engine-qa"},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["validation"]["overall_status"] == "needs_review"

    approve_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator", "rationale": "Proceed"},
    )
    assert approve_response.status_code == 200

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 409
    assert "explicit human review state" in generate_response.json()["detail"]
