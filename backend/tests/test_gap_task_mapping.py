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


def test_approved_gaps_map_to_owner_specific_templates() -> None:
    run_id = _prepare_validated_approved_run()

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 200
    payload = generate_response.json()

    assert payload["created_count"] >= 1
    owners = {task["owner"] for task in payload["tasks"]}
    assert "lab-coordinator" in owners or "nephrology-coordinator" in owners


def test_tasks_link_to_originating_gap_ids() -> None:
    run_id = _prepare_validated_approved_run()

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 200

    tasks = generate_response.json()["tasks"]
    for task in tasks:
        assert task["originating_gap_id"]
        assert task["template_id"]


def test_missing_mapping_flagged_without_orphan_tasks() -> None:
    create_run_response = client.post(
        "/api/v1/orchestration/runs",
        json={
            "patient_id": "PT-0001",
            "recommendations": [
                {
                    "gap_id": "GAP-UNMAPPED-DEMO",
                    "recommendation_id": "REC-UNMAPPED-XYZ",
                    "title": "Unknown Recommendation",
                }
            ],
        },
    )
    assert create_run_response.status_code == 200
    run_id = create_run_response.json()["run"]["run_id"]

    approve_response = client.post(
        f"/api/v1/orchestration/runs/{run_id}/decision",
        json={"decision": "approve", "actor": "coordinator", "rationale": "Proceed"},
    )
    assert approve_response.status_code == 200

    generate_response = client.post(f"/api/v1/orchestration/runs/{run_id}/tasks/generate")
    assert generate_response.status_code == 409
    assert "missing task mappings" in generate_response.json()["detail"]

    list_tasks_response = client.get(f"/api/v1/orchestration/runs/{run_id}/tasks")
    assert list_tasks_response.status_code == 200
    assert list_tasks_response.json()["count"] == 0
