from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analysis_runs_only_on_explicit_trigger() -> None:
    before_response = client.get("/api/v1/orchestration/analysis", params={"patient_id": "PT-0001"})
    assert before_response.status_code == 200
    before_count = before_response.json()["count"]

    profile_response = client.get("/api/v1/patients/PT-0001/profile")
    assert profile_response.status_code == 200

    after_profile_response = client.get("/api/v1/orchestration/analysis", params={"patient_id": "PT-0001"})
    assert after_profile_response.status_code == 200
    assert after_profile_response.json()["count"] == before_count

    trigger_response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
    assert trigger_response.status_code == 200

    after_trigger_response = client.get("/api/v1/orchestration/analysis", params={"patient_id": "PT-0001"})
    assert after_trigger_response.status_code == 200
    assert after_trigger_response.json()["count"] == before_count + 1


def test_analysis_result_is_persisted_and_queryable() -> None:
    trigger_response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
    assert trigger_response.status_code == 200

    analysis = trigger_response.json()["analysis"]
    analysis_id = analysis["analysis_id"]

    read_response = client.get(f"/api/v1/orchestration/analysis/{analysis_id}")
    assert read_response.status_code == 200
    persisted = read_response.json()["analysis"]

    assert persisted["analysis_id"] == analysis_id
    assert persisted["patient_id"] == "PT-0001"
    assert persisted["run_id"]
    assert persisted["status"] == "completed"


def test_analysis_payload_contains_required_fields() -> None:
    trigger_response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
    assert trigger_response.status_code == 200

    analysis = trigger_response.json()["analysis"]
    assert analysis["risk"]
    assert isinstance(analysis["gaps"], list)
    assert len(analysis["gaps"]) >= 1
    assert analysis["reasoning"]
    assert isinstance(analysis["evidence"], list)
    assert analysis["confidence"] >= 0

    first_gap = analysis["gaps"][0]
    assert first_gap["reasoning"]
    assert first_gap["evidence"]
    assert first_gap["confidence"] >= 0
