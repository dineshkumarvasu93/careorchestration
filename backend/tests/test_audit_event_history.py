from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import app
from app.policy import policy_audit_log

client = TestClient(app)


def _find_latest_event(event_type: str) -> dict[str, object]:
    response = client.get("/api/v1/policy/audit/events", params={"limit": 200})
    assert response.status_code == 200
    events = response.json()["events"]
    filtered = [event for event in events if event.get("event_type") == event_type]
    assert filtered
    return filtered[-1]


def _create_patient_run(patient_id: str = "PT-0001") -> str:
    analysis_response = client.post(
        "/api/v1/orchestration/analysis/trigger",
        json={"patient_id": patient_id},
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()["analysis"]

    validation_response = client.post(
        f"/api/v1/orchestration/analysis/{analysis['analysis_id']}/validate",
        json={"confidence_threshold": 0.7, "actor": "qa-reviewer"},
    )
    assert validation_response.status_code == 200

    run_id = analysis["run_id"]
    decision_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "qa-coordinator", "rationale": "approved for audit test"},
    )
    assert decision_response.status_code == 200

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 200
    return run_id


def test_audit_event_contains_required_us014_fields() -> None:
    disclaimer_response = client.get("/api/v1/policy/disclaimer", params={"channel": "cx"})
    assert disclaimer_response.status_code == 200

    event = _find_latest_event("disclaimer")
    assert event["action"] == "shown"
    assert event["timestamp_utc"]
    assert event["actor"]
    assert event["channel"] == "cx"
    assert event["payload_hash"]
    assert event["current_hash"]


def test_audit_hash_chain_integrity_check_passes() -> None:
    integrity_response = client.get("/api/v1/policy/audit/integrity")
    assert integrity_response.status_code == 200

    payload = integrity_response.json()
    assert payload["event_count"] >= 1
    assert payload["is_valid"] is True
    assert payload["failures"] == []


def test_audit_integrity_detects_tampering() -> None:
    client.get("/api/v1/policy/disclaimer", params={"channel": "ui"})

    last_event = policy_audit_log._events[-1]
    tampered_event = replace(last_event, details={"tampered": True})
    policy_audit_log._events[-1] = tampered_event

    try:
        integrity_response = client.get("/api/v1/policy/audit/integrity")
        assert integrity_response.status_code == 200
        payload = integrity_response.json()
        assert payload["is_valid"] is False
        assert any(failure["error"] == "payload_hash_mismatch" for failure in payload["failures"])
    finally:
        policy_audit_log._events[-1] = last_event


def test_patient_timeline_reconstruction_is_complete() -> None:
    run_id = _create_patient_run(patient_id="PT-0001")

    timeline_response = client.get("/api/v1/policy/audit/patients/PT-0001")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()

    assert timeline["patient_id"] == "PT-0001"
    assert timeline["count"] >= 1

    run_events = [event for event in timeline["events"] if event.get("run_id") == run_id]
    assert run_events

    event_types = {event["event_type"] for event in run_events}
    assert "analysis" in event_types
    assert "analysis_validation" in event_types
    assert "orchestration_gate" in event_types
    assert "notification_dispatch" in event_types

    for event in run_events:
        assert event["timestamp_utc"]
        assert event["actor"]
        assert event["channel"]
        assert event["payload_hash"]
