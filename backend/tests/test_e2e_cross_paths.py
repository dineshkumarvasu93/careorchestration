from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _full_happy_path_run() -> tuple[str, str]:
    analysis_response = client.post(
        "/api/v1/orchestration/analysis/trigger",
        json={"patient_id": "PT-0001"},
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()["analysis"]

    validate_response = client.post(
        f"/api/v1/orchestration/analysis/{analysis['analysis_id']}/validate",
        json={"confidence_threshold": 0.8, "actor": "rule-engine"},
    )
    assert validate_response.status_code == 200

    run_id = analysis["run_id"]
    decision_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator-happy", "rationale": "Proceed"},
    )
    assert decision_response.status_code == 200

    generate_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/generate",
        json={"actor": "coordinator-happy"},
    )
    assert generate_response.status_code == 200

    return run_id, analysis["analysis_id"]


def test_e2e_happy_path_generates_tasks_after_approval() -> None:
    run_id, _ = _full_happy_path_run()

    tasks_response = client.get(f"/api/v1/orchestration/runs/{run_id}/tasks")
    assert tasks_response.status_code == 200
    assert tasks_response.json()["count"] >= 1


def test_e2e_negative_path_no_task_without_approval_is_enforced() -> None:
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

    blocked_before_decision = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/generate",
        json={"actor": "coordinator-negative"},
    )
    assert blocked_before_decision.status_code == 409
    assert "approval required" in blocked_before_decision.json()["detail"]

    reject_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "reject", "actor": "coordinator-negative", "rationale": "Not safe to proceed"},
    )
    assert reject_response.status_code == 200

    blocked_after_reject = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/generate",
        json={"actor": "coordinator-negative"},
    )
    assert blocked_after_reject.status_code == 409
    assert "terminated" in blocked_after_reject.json()["detail"]
