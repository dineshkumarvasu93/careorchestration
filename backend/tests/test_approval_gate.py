from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_run() -> str:
    response = client.post(
        "/api/v1/orchestration/runs",
        json={
            "patient_id": "PT-0001",
            "recommendations": [
                {"recommendation_id": "REC-001", "title": "Order UACR"},
                {"recommendation_id": "REC-002", "title": "Schedule nephrology follow-up"},
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["run"]["run_id"]


def test_no_approval_means_no_task_creation() -> None:
    run_id = _create_run()

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 409
    assert "approval required" in generate_response.json()["detail"]

    list_response = client.get(f"/api/v1/orchestration/runs/{run_id}/tasks")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0


def test_approve_enables_downstream_task_generation() -> None:
    run_id = _create_run()

    decision_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator-1", "rationale": "Ready to proceed"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["run"]["decision"] == "approve"

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 200
    assert generate_response.json()["status"] == "generated"
    assert generate_response.json()["created_count"] == 2


def test_reject_terminates_orchestration() -> None:
    run_id = _create_run()

    decision_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "reject", "actor": "coordinator-2", "rationale": "Data quality concern"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["run"]["status"] == "rejected"
    assert decision_response.json()["run"]["terminated"] is True

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 409
    assert "terminated" in generate_response.json()["detail"]

    list_response = client.get(f"/api/v1/orchestration/runs/{run_id}/tasks")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0
