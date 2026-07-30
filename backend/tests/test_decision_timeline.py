from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_run() -> str:
    response = client.post(
        "/api/v1/orchestration/runs",
        json={
            "patient_id": "PT-0002",
            "recommendations": [{"recommendation_id": "REC-001", "title": "Order UACR"}],
        },
    )
    assert response.status_code == 200
    return response.json()["run"]["run_id"]


def test_decision_event_captures_actor_outcome_rationale_and_timestamp() -> None:
    run_id = _create_run()

    decision_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "reject", "actor": "coordinator-qa", "rationale": "Insufficient context"},
    )
    assert decision_response.status_code == 200

    timeline_response = client.get(f"/api/v1/orchestration/runs/{run_id}/timeline")
    assert timeline_response.status_code == 200
    events = timeline_response.json()["events"]
    decision_events = [event for event in events if event["event_type"] == "decision_recorded"]
    assert len(decision_events) == 1

    event = decision_events[0]
    assert event["actor"] == "coordinator-qa"
    assert event["details"]["outcome"] == "reject"
    assert event["details"]["rationale"] == "Insufficient context"
    assert event["timestamp_utc"]


def test_append_only_semantics_prevent_decision_overwrite() -> None:
    run_id = _create_run()

    first = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator-1", "rationale": "Ready"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "reject", "actor": "coordinator-2", "rationale": "Changing my mind"},
    )
    assert second.status_code == 409
    assert "already recorded" in second.json()["detail"]


def test_timeline_endpoint_is_queryable_for_run_history() -> None:
    run_id = _create_run()

    decision_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator-3", "rationale": "Proceed"},
    )
    assert decision_response.status_code == 200

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 200

    timeline_response = client.get(f"/api/v1/orchestration/runs/{run_id}/timeline")
    assert timeline_response.status_code == 200

    payload = timeline_response.json()
    assert payload["run_id"] == run_id
    assert payload["count"] >= 3

    event_types = [event["event_type"] for event in payload["events"]]
    assert "run_created" in event_types
    assert "decision_recorded" in event_types
    assert "tasks_generated" in event_types
