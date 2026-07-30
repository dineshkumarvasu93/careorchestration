import os
import time

from fastapi.testclient import TestClient

from app.analysis_engine import analysis_engine
from app.main import app

client = TestClient(app)


class _OfflineGuidelineAdapter:
    def is_healthy(self) -> bool:
        return False


class _OfflineAiAdapter:
    def is_healthy(self) -> bool:
        return False


class _HealthyGuidelineAdapter:
    def is_healthy(self) -> bool:
        return True

    def get_context(self, profile: dict[str, object]) -> list[dict[str, str]]:
        return [{"code": "LIVE-CTX", "statement": "Healthy guideline context"}]


class _HealthyAiAdapter:
    def is_healthy(self) -> bool:
        return True

    def generate(
        self,
        profile: dict[str, object],
        guideline_context: list[dict[str, str]],
    ) -> dict[str, object]:
        return {
            "risk_level": "high",
            "confidence": 0.95,
            "gaps": [
                {
                    "gap_id": "LIVE-GAP-RECOVERY",
                    "recommendation_id": "REC-LIVE-001",
                    "title": "Live recovery recommendation",
                    "reasoning": "Healthy dependencies active",
                    "evidence": guideline_context,
                    "confidence": 0.95,
                    "severity": "high",
                }
            ],
            "reasoning": "Live path available",
            "evidence": guideline_context,
            "triggered_at_utc": "2026-01-01T00:00:00+00:00",
        }


def _set_live_env() -> tuple[str | None, str | None, str | None]:
    previous_mode = os.environ.get("ANALYSIS_MODE")
    previous_guideline_url = os.environ.get("GUIDELINE_SERVICE_URL")
    previous_ai_url = os.environ.get("AI_SERVICE_URL")

    os.environ["ANALYSIS_MODE"] = "live"
    os.environ["GUIDELINE_SERVICE_URL"] = "https://offline-guideline.example"
    os.environ["AI_SERVICE_URL"] = "https://offline-ai.example"

    return previous_mode, previous_guideline_url, previous_ai_url


def _restore_live_env(previous_mode: str | None, previous_guideline_url: str | None, previous_ai_url: str | None) -> None:
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


def test_full_demo_succeeds_with_dependencies_offline_and_collects_evidence() -> None:
    previous_mode, previous_guideline_url, previous_ai_url = _set_live_env()
    original_guideline_factory = analysis_engine._live_guideline_adapter_factory
    original_ai_factory = analysis_engine._live_ai_adapter_factory

    analysis_engine._live_guideline_adapter_factory = lambda _base_url: _OfflineGuidelineAdapter()
    analysis_engine._live_ai_adapter_factory = lambda _base_url: _OfflineAiAdapter()

    try:
        timings: dict[str, float] = {}

        started = time.perf_counter()
        analysis_response = client.post(
            "/api/v1/orchestration/analysis/trigger",
            json={"patient_id": "PT-0001"},
        )
        timings["analysis_trigger_seconds"] = round(time.perf_counter() - started, 4)
        assert analysis_response.status_code == 200

        analysis = analysis_response.json()["analysis"]
        assert analysis["adapter_mode"] == "mock"

        started = time.perf_counter()
        validate_response = client.post(
            f"/api/v1/orchestration/analysis/{analysis['analysis_id']}/validate",
            json={"confidence_threshold": 0.8, "actor": "rule-engine"},
        )
        timings["validation_seconds"] = round(time.perf_counter() - started, 4)
        assert validate_response.status_code == 200

        started = time.perf_counter()
        decision_response = client.post(
            f"/api/v1/orchestration/runs/{analysis['run_id']}/decision",
            json={"decision": "approve", "actor": "coordinator-offline", "rationale": "Proceed"},
        )
        timings["decision_seconds"] = round(time.perf_counter() - started, 4)
        assert decision_response.status_code == 200

        started = time.perf_counter()
        generate_response = client.post(
            f"/api/v1/orchestration/runs/{analysis['run_id']}/tasks/generate",
            json={"actor": "coordinator-offline"},
        )
        timings["task_generation_seconds"] = round(time.perf_counter() - started, 4)
        assert generate_response.status_code == 200
        assert generate_response.json()["created_count"] >= 1

        outage_evidence = {
            "dependency_state": "offline",
            "fallback_mode": analysis["adapter_mode"],
            "timings": timings,
        }

        assert outage_evidence["fallback_mode"] == "mock"
        assert outage_evidence["timings"]["analysis_trigger_seconds"] <= 1.5
    finally:
        analysis_engine._live_guideline_adapter_factory = original_guideline_factory
        analysis_engine._live_ai_adapter_factory = original_ai_factory
        _restore_live_env(previous_mode, previous_guideline_url, previous_ai_url)


def test_recovery_to_live_mode_is_verified_after_offline_rehearsal() -> None:
    previous_mode, previous_guideline_url, previous_ai_url = _set_live_env()
    original_guideline_factory = analysis_engine._live_guideline_adapter_factory
    original_ai_factory = analysis_engine._live_ai_adapter_factory

    try:
        analysis_engine._live_guideline_adapter_factory = lambda _base_url: _OfflineGuidelineAdapter()
        analysis_engine._live_ai_adapter_factory = lambda _base_url: _OfflineAiAdapter()

        offline_response = client.post(
            "/api/v1/orchestration/analysis/trigger",
            json={"patient_id": "PT-0001"},
        )
        assert offline_response.status_code == 200
        assert offline_response.json()["analysis"]["adapter_mode"] == "mock"

        analysis_engine._live_guideline_adapter_factory = lambda _base_url: _HealthyGuidelineAdapter()
        analysis_engine._live_ai_adapter_factory = lambda _base_url: _HealthyAiAdapter()

        recovery_response = client.post(
            "/api/v1/orchestration/analysis/trigger",
            json={"patient_id": "PT-0001"},
        )
        assert recovery_response.status_code == 200
        recovered = recovery_response.json()["analysis"]
        assert recovered["adapter_mode"] == "live"
        assert recovered["gaps"][0]["gap_id"] == "LIVE-GAP-RECOVERY"
    finally:
        analysis_engine._live_guideline_adapter_factory = original_guideline_factory
        analysis_engine._live_ai_adapter_factory = original_ai_factory
        _restore_live_env(previous_mode, previous_guideline_url, previous_ai_url)
