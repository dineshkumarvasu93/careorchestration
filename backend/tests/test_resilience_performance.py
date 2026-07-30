import os
import time

from fastapi.testclient import TestClient

from app.analysis_engine import analysis_engine
from app.main import app

client = TestClient(app)


class _UnhealthyGuidelineAdapter:
    def is_healthy(self) -> bool:
        return False


class _UnhealthyAiAdapter:
    def is_healthy(self) -> bool:
        return False


def test_mock_mode_offline_flow_meets_latency_target() -> None:
    previous_mode = os.environ.get("ANALYSIS_MODE")
    previous_guideline_url = os.environ.get("GUIDELINE_SERVICE_URL")
    previous_ai_url = os.environ.get("AI_SERVICE_URL")

    os.environ["ANALYSIS_MODE"] = "live"
    os.environ["GUIDELINE_SERVICE_URL"] = "https://offline-guideline.example"
    os.environ["AI_SERVICE_URL"] = "https://offline-ai.example"

    original_guideline_factory = analysis_engine._live_guideline_adapter_factory
    original_ai_factory = analysis_engine._live_ai_adapter_factory
    analysis_engine._live_guideline_adapter_factory = lambda _base_url: _UnhealthyGuidelineAdapter()
    analysis_engine._live_ai_adapter_factory = lambda _base_url: _UnhealthyAiAdapter()

    try:
        started_at = time.perf_counter()
        response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
        elapsed_seconds = time.perf_counter() - started_at
    finally:
        analysis_engine._live_guideline_adapter_factory = original_guideline_factory
        analysis_engine._live_ai_adapter_factory = original_ai_factory

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
    assert analysis["adapter_mode"] == "mock"

    # Cross-cutting target: mock-mode fallback should complete well under 1.5s offline.
    assert elapsed_seconds <= 1.5
