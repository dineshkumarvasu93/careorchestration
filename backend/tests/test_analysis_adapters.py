import os

from fastapi.testclient import TestClient

from app.main import app
from app.analysis_engine import analysis_engine

client = TestClient(app)


def test_mock_mode_serves_deterministic_fixture_gaps() -> None:
    previous_mode = os.environ.get("ANALYSIS_MODE")
    os.environ["ANALYSIS_MODE"] = "mock"
    try:
        response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
    finally:
        if previous_mode is None:
            os.environ.pop("ANALYSIS_MODE", None)
        else:
            os.environ["ANALYSIS_MODE"] = previous_mode

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["adapter_mode"] == "mock"
    assert analysis["risk"] == "high"

    gap_ids = {gap["gap_id"] for gap in analysis["gaps"]}
    assert "GAP-UACR-MISSING" in gap_ids
    assert "GAP-EGFR-DECLINE" in gap_ids
    assert "GAP-CKD-HIGH-RISK-PLAN" in gap_ids


def test_john_smith_expected_high_risk_with_three_gaps() -> None:
    previous_mode = os.environ.get("ANALYSIS_MODE")
    os.environ["ANALYSIS_MODE"] = "mock"
    try:
        response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
    finally:
        if previous_mode is None:
            os.environ.pop("ANALYSIS_MODE", None)
        else:
            os.environ["ANALYSIS_MODE"] = previous_mode

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["risk"] == "high"
    assert len(analysis["gaps"]) == 3


def test_live_mode_uses_external_adapters_when_healthy(monkeypatch) -> None:
    previous_mode = os.environ.get("ANALYSIS_MODE")
    previous_guideline_url = os.environ.get("GUIDELINE_SERVICE_URL")
    previous_ai_url = os.environ.get("AI_SERVICE_URL")

    os.environ["ANALYSIS_MODE"] = "live"
    os.environ["GUIDELINE_SERVICE_URL"] = "https://guideline.example"
    os.environ["AI_SERVICE_URL"] = "https://ai.example"

    class FakeLiveGuidelineAdapter:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def is_healthy(self) -> bool:
            return True

        def get_context(self, profile: dict[str, object]) -> list[dict[str, str]]:
            return [{"code": "LIVE-CTX", "statement": "Live guideline context"}]

    class FakeLiveAiAdapter:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def is_healthy(self) -> bool:
            return True

        def generate(
            self,
            profile: dict[str, object],
            guideline_context: list[dict[str, str]],
        ) -> dict[str, object]:
            return {
                "risk_level": "high",
                "confidence": 0.97,
                "gaps": [
                    {
                        "gap_id": "LIVE-GAP-001",
                        "recommendation_id": "LIVE-REC-001",
                        "title": "Live recommendation",
                        "reasoning": "Generated from live service",
                        "evidence": guideline_context,
                        "confidence": 0.97,
                        "severity": "high",
                    }
                ],
                "reasoning": "Live analysis path",
                "evidence": guideline_context,
                "triggered_at_utc": "2026-01-01T00:00:00+00:00",
            }

    monkeypatch.setattr(
        analysis_engine,
        "_live_guideline_adapter_factory",
        lambda base_url: FakeLiveGuidelineAdapter(base_url=base_url),
    )
    monkeypatch.setattr(
        analysis_engine,
        "_live_ai_adapter_factory",
        lambda base_url: FakeLiveAiAdapter(base_url=base_url),
    )

    try:
        response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
    finally:
        if previous_mode is None:
            os.environ.pop("ANALYSIS_MODE", None)
        else:
            os.environ["ANALYSIS_MODE"] = previous_mode

        if previous_guideline_url is None:
            os.environ.pop("GUIDELINE_SERVICE_URL", None)
        else:
            os.environ["GUIDELINE_SERVICE_URL"] = previous_guideline_url

        if previous_ai_url is None:
            os.environ.pop("AI_SERVICE_URL", None)
        else:
            os.environ["AI_SERVICE_URL"] = previous_ai_url

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["adapter_mode"] == "live"
    assert analysis["gaps"][0]["gap_id"] == "LIVE-GAP-001"
