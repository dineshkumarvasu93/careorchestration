from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _prepare_validated_approved_run() -> str:
    analysis_response = client.post(
        "/api/v1/orchestration/analysis/trigger",
        json={"patient_id": "PT-0001"},
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()["analysis"]
    analysis_id = str(analysis["analysis_id"])
    run_id = str(analysis["run_id"])

    validate_response = client.post(
        f"/api/v1/orchestration/analysis/{analysis_id}/validate",
        json={"confidence_threshold": 0.8, "actor": "rule-engine"},
    )
    assert validate_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator", "rationale": "Proceed"},
    )
    assert approve_response.status_code == 200

    return run_id


def test_owner_and_patient_notifications_trigger_on_task_creation() -> None:
    run_id = _prepare_validated_approved_run()

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate", json={})
    assert generate_response.status_code == 200

    notifications = generate_response.json()["notifications"]
    recipient_types = {entry["recipient_type"] for entry in notifications["logs"]}
    assert "owner" in recipient_types
    assert "patient" in recipient_types


def test_retry_backoff_are_configurable() -> None:
    run_id = _prepare_validated_approved_run()

    generate_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/generate",
        json={
            "notification_policy": {
                "max_retries": 3,
                "backoff_ms": 150,
            }
        },
    )
    assert generate_response.status_code == 200

    policy = generate_response.json()["notifications"]["policy"]
    assert policy["max_retries"] == 3
    assert policy["backoff_ms"] == 150


def test_failure_outcomes_include_retry_attempt_logs() -> None:
    run_id = _prepare_validated_approved_run()

    generate_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/generate",
        json={
            "notification_policy": {
                "max_retries": 2,
                "backoff_ms": 100,
            },
            "notification_simulation": {
                "fail_first_attempts": {
                    "owner:lab-coordinator": 2,
                    "patient:PT-0001": 3,
                }
            },
        },
    )
    assert generate_response.status_code == 200

    notifications = generate_response.json()["notifications"]
    assert notifications["failure_count"] >= 1

    patient_logs = [
        item
        for item in notifications["logs"]
        if item["recipient_key"] == "patient:PT-0001"
    ]
    assert len(patient_logs) == 1
    assert patient_logs[0]["final_status"] == "failed"
    assert len(patient_logs[0]["attempts"]) == 3
    assert patient_logs[0]["attempts"][-1]["status"] == "failed"
