from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _prepare_run_with_tasks() -> tuple[str, str]:
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

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate", json={})
    assert generate_response.status_code == 200
    first_task_id = generate_response.json()["tasks"][0]["task_id"]

    return run_id, first_task_id


def test_state_transitions_are_validated_and_timestamped() -> None:
    run_id, task_id = _prepare_run_with_tasks()

    transition_1 = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/{task_id}/status",
        json={"status": "in_progress", "actor": "owner-1", "reason": "work_started"},
    )
    assert transition_1.status_code == 200

    transition_2 = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/{task_id}/status",
        json={"status": "completed", "actor": "owner-1", "reason": "work_done"},
    )
    assert transition_2.status_code == 200

    task = transition_2.json()["task"]
    assert task["status"] == "completed"
    assert task["updated_at_utc"]
    assert len(task["history"]) >= 3

    invalid_transition = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/{task_id}/status",
        json={"status": "created", "actor": "owner-1", "reason": "rollback"},
    )
    assert invalid_transition.status_code == 409


def test_overdue_tasks_emit_escalation_events() -> None:
    run_id, task_id = _prepare_run_with_tasks()

    # Move task into in-progress.
    transition = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/{task_id}/status",
        json={"status": "in_progress", "actor": "owner-1", "reason": "work_started"},
    )
    assert transition.status_code == 200

    scheduler_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    escalation_check = client.post(
        f"/api/v1/orchestration/runs/{run_id}/escalation/check",
        json={"actor": "scheduler", "current_time_utc": scheduler_time},
    )
    assert escalation_check.status_code == 200
    assert escalation_check.json()["escalated_count"] >= 1

    tracking_after = client.get(f"/api/v1/orchestration/runs/{run_id}/tracking")
    assert tracking_after.status_code == 200
    after_task = next(item for item in tracking_after.json()["tasks"] if item["task_id"] == task_id)
    assert after_task["escalated"] is True
    assert len(after_task["escalation_events"]) >= 1


def test_tracking_view_shows_statuses_and_escalation_markers() -> None:
    run_id, task_id = _prepare_run_with_tasks()

    transition = client.post(
        f"/api/v1/orchestration/runs/{run_id}/tasks/{task_id}/status",
        json={"status": "in_progress", "actor": "owner-1", "reason": "work_started"},
    )
    assert transition.status_code == 200

    tracking = client.get(f"/api/v1/orchestration/runs/{run_id}/tracking")
    assert tracking.status_code == 200

    payload = tracking.json()
    assert payload["run_id"] == run_id
    assert payload["task_count"] >= 1
    assert isinstance(payload["status_counts"], dict)
    assert any(task["task_id"] == task_id for task in payload["tasks"])
