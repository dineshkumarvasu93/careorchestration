from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _run_ui_approve_flow(patient_id: str) -> dict[str, object]:
    trigger = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": patient_id})
    assert trigger.status_code == 200
    analysis = trigger.json()["analysis"]
    analysis_id = str(analysis["analysis_id"])
    run_id = str(analysis["run_id"])

    validate = client.post(
        f"/api/v1/orchestration/analysis/{analysis_id}/validate",
        json={"confidence_threshold": 0.8, "actor": "ui-rule-engine"},
    )
    assert validate.status_code == 200

    decide = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "ui-coordinator", "rationale": "Proceed"},
    )
    assert decide.status_code == 200

    generate = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate", json={})
    assert generate.status_code == 200

    return {
        "analysis": analysis,
        "tasks": generate.json()["tasks"],
        "run_id": run_id,
        "analysis_id": analysis_id,
    }


def _cx(session_id: str, action: str, parameters: dict[str, object]) -> dict[str, object]:
    response = client.post(
        "/api/v1/orchestration/cx/webhook",
        json={
            "session_id": session_id,
            "action": action,
            "parameters": parameters,
        },
    )
    assert response.status_code == 200
    return response.json()


def _run_cx_approve_flow(query: str) -> dict[str, object]:
    session_id = f"cx-parity-{query.lower()}"
    search = _cx(session_id, "search", {"query": query})
    selected_patient_id = str(search["payload"]["result"]["selected_patient_id"])
    assert selected_patient_id

    analyze = _cx(session_id, "analyze", {})
    analysis_payload = analyze["payload"]["result"]
    run_id = str(analysis_payload["run_id"])

    _cx(session_id, "review", {})
    _cx(session_id, "decision", {"decision": "approve", "rationale": "Proceed"})
    confirm = _cx(session_id, "confirm", {})

    return {
        "analysis": analysis_payload,
        "tasks": confirm["payload"]["result"]["tasks"],
        "run_id": run_id,
        "analysis_id": str(analysis_payload["analysis_id"]),
        "patient_id": selected_patient_id,
    }


def _normalize_gap_signature(gap: dict[str, object]) -> tuple[str, str]:
    return (
        str(gap.get("gap_id", "")),
        str(gap.get("recommendation_id", "")),
    )


def _normalize_task_signature(task: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(task.get("originating_gap_id", "")),
        str(task.get("template_id", "")),
        str(task.get("owner", "")),
    )


def test_risk_and_gaps_match_for_identical_fixture() -> None:
    ui = _run_ui_approve_flow("PT-0001")
    cx = _run_cx_approve_flow("John")

    assert ui["analysis"]["risk"] == cx["analysis"]["risk"]

    ui_gaps = {
        _normalize_gap_signature(gap)
        for gap in ui["analysis"]["gaps"]
        if isinstance(gap, dict)
    }
    cx_gaps = {
        _normalize_gap_signature(gap)
        for gap in cx["analysis"]["gaps"]
        if isinstance(gap, dict)
    }
    assert ui_gaps == cx_gaps


def test_tasks_and_owners_match_for_identical_decision() -> None:
    ui = _run_ui_approve_flow("PT-0001")
    cx = _run_cx_approve_flow("John")

    ui_tasks = {
        _normalize_task_signature(task)
        for task in ui["tasks"]
        if isinstance(task, dict)
    }
    cx_tasks = {
        _normalize_task_signature(task)
        for task in cx["tasks"]
        if isinstance(task, dict)
    }
    assert ui_tasks == cx_tasks


def test_parity_mismatch_would_fail_release_gate() -> None:
    ui = _run_ui_approve_flow("PT-0001")
    cx = _run_cx_approve_flow("John")

    # This assertion is the release gate: any channel divergence fails test execution.
    assert ui["analysis"]["risk"] == cx["analysis"]["risk"]
    assert len(ui["tasks"]) == len(cx["tasks"])
