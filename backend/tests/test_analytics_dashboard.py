from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.orchestration_state import orchestration_run_store

client = TestClient(app)


def _create_run(patient_id: str = "PT-0001") -> str:
    response = client.post(
        "/api/v1/orchestration/runs",
        json={
            "patient_id": patient_id,
            "recommendations": [
                {"recommendation_id": "REC-001", "title": "Order UACR"},
                {"recommendation_id": "REC-002", "title": "Schedule Follow-up"},
            ],
        },
    )
    assert response.status_code == 200
    return str(response.json()["run"]["run_id"])


def _set_run_timestamps(run_id: str, created_at: datetime, decision_at: datetime, tasks_generated_at: datetime | None) -> None:
    run = orchestration_run_store._runs[run_id]
    run["created_at_utc"] = created_at.isoformat()

    decision_record = run.get("decision_record")
    if isinstance(decision_record, dict):
        decision_record["timestamp_utc"] = decision_at.isoformat()

    timeline = run.get("timeline", [])
    if isinstance(timeline, list):
        for event in timeline:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("event_type", ""))
            if event_type == "decision_recorded":
                event["timestamp_utc"] = decision_at.isoformat()
            if tasks_generated_at and event_type == "tasks_generated":
                event["timestamp_utc"] = tasks_generated_at.isoformat()


def test_approval_and_conversion_metrics_are_returned_correctly() -> None:
    approved_run_id = _create_run("PT-0001")
    rejected_run_id = _create_run("PT-0002")
    _create_run("PT-0001")

    approve_response = client.post(
        f"/api/v1/orchestration/runs/{approved_run_id}/decision",
        json={"decision": "approve", "actor": "coordinator-a", "rationale": "Proceed"},
    )
    assert approve_response.status_code == 200

    generate_response = client.post(f"/api/v1/orchestration/runs/{approved_run_id}/tasks/generate", json={})
    assert generate_response.status_code == 200

    reject_response = client.post(
        f"/api/v1/orchestration/runs/{rejected_run_id}/decision",
        json={"decision": "reject", "actor": "coordinator-b", "rationale": "Hold"},
    )
    assert reject_response.status_code == 200

    analytics_response = client.get("/api/v1/orchestration/analytics")
    assert analytics_response.status_code == 200

    payload = analytics_response.json()
    approval = payload["approval"]
    conversion = payload["conversion"]

    assert approval["total_runs"] >= 3
    assert approval["decided_runs"] >= 2
    assert approval["approved_runs"] >= 1
    assert approval["rejected_runs"] >= 1
    assert conversion["tasks_generated_runs"] >= 1
    assert conversion["conversion_rate_pct"] >= 0


def test_latency_metrics_are_queryable() -> None:
    run_id = _create_run("PT-0001")

    approve_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator-c", "rationale": "Proceed"},
    )
    assert approve_response.status_code == 200

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate", json={})
    assert generate_response.status_code == 200

    start = datetime.now(timezone.utc)
    decision_at = start + timedelta(seconds=40)
    generated_at = start + timedelta(seconds=100)
    _set_run_timestamps(
        run_id=run_id,
        created_at=start,
        decision_at=decision_at,
        tasks_generated_at=generated_at,
    )

    analytics_response = client.get("/api/v1/orchestration/analytics")
    assert analytics_response.status_code == 200

    latency = analytics_response.json()["latency"]
    assert latency["decision_latency_count"] >= 1
    assert latency["task_generation_latency_count"] >= 1
    assert latency["end_to_end_latency_count"] >= 1
    assert latency["average_decision_latency_seconds"] >= 0
    assert latency["average_task_generation_latency_seconds"] >= 0
    assert latency["average_end_to_end_latency_seconds"] >= 0


def test_dashboard_labels_and_values_are_consistent() -> None:
    analytics_response = client.get("/api/v1/orchestration/analytics")
    assert analytics_response.status_code == 200

    widgets = analytics_response.json()["widgets"]
    keys = {widget["key"] for widget in widgets}
    labels = {widget["label"] for widget in widgets}

    assert "approval_rate" in keys
    assert "conversion_rate" in keys
    assert "avg_decision_latency" in keys
    assert "avg_end_to_end_latency" in keys

    assert "Approval Rate" in labels
    assert "Conversion Rate" in labels
    assert "Avg Decision Latency (s)" in labels
    assert "Avg End-to-End Latency (s)" in labels

    for widget in widgets:
        assert str(widget.get("value", "")).strip() != ""
