from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _webhook(action: str, session: str, parameters: dict[str, object]) -> dict[str, object]:
    response = client.post(
        "/api/v1/orchestration/cx/webhook",
        json={
            "action": action,
            "session_id": session,
            "parameters": parameters,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_conversation_journey_approve_path() -> None:
    session = "cx-session-approve-001"

    search = _webhook("search", session, {"query": "John"})
    assert search["payload"]["result"]["match_count"] >= 1
    selected_patient_id = search["payload"]["result"]["selected_patient_id"]
    assert selected_patient_id == "PT-0001"

    analyze = _webhook("analyze", session, {})
    analysis_id = analyze["payload"]["result"]["analysis_id"]
    run_id = analyze["payload"]["result"]["run_id"]
    assert analysis_id
    assert run_id

    review = _webhook("review", session, {})
    assert review["payload"]["result"]["analysis_id"] == analysis_id
    assert review["payload"]["result"]["run_id"] == run_id

    decision = _webhook("decision", session, {"decision": "approve", "rationale": "Looks good"})
    assert decision["payload"]["result"]["decision"] == "approve"

    confirm = _webhook("confirm", session, {})
    assert confirm["payload"]["result"]["confirmation"] == "approved"
    assert confirm["payload"]["result"]["task_count"] >= 1


def test_conversation_journey_reject_path_preserves_context() -> None:
    session = "cx-session-reject-001"

    _webhook("search", session, {"query": "John"})
    analyze = _webhook("analyze", session, {})
    run_id = analyze["payload"]["result"]["run_id"]

    _webhook("review", session, {})
    decision = _webhook("decision", session, {"decision": "reject", "rationale": "Not ready"})
    assert decision["payload"]["result"]["run_status"] == "rejected"

    confirm = _webhook("confirm", session, {})
    assert confirm["payload"]["result"]["confirmation"] == "rejected"
    assert confirm["payload"]["result"]["task_count"] == 0

    params = confirm["sessionInfo"]["parameters"]
    assert params["session_id"] == session
    assert params["run_id"] == run_id
    assert params["decision"] == "reject"


def test_webhook_and_ui_use_same_orchestration_state() -> None:
    session = "cx-session-parity-001"

    _webhook("search", session, {"query": "John"})
    analyze = _webhook("analyze", session, {})
    run_id = analyze["payload"]["result"]["run_id"]

    _webhook("review", session, {})
    _webhook("decision", session, {"decision": "approve", "rationale": "Proceed"})
    confirm = _webhook("confirm", session, {})

    tasks = confirm["payload"]["result"]["tasks"]
    list_response = client.get(f"/api/v1/orchestration/runs/{run_id}/tasks")
    assert list_response.status_code == 200
    api_tasks = list_response.json()["tasks"]

    assert len(tasks) == len(api_tasks)
    assert {task["task_id"] for task in tasks} == {task["task_id"] for task in api_tasks}
