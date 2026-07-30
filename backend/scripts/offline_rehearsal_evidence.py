from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass

from fastapi.testclient import TestClient

from app.analysis_engine import analysis_engine
from app.main import app


@dataclass(frozen=True)
class RehearsalEvidence:
    dependency_state: str
    fallback_mode: str
    timings_seconds: dict[str, float]
    run_id: str
    analysis_id: str
    task_count: int


class _OfflineGuidelineAdapter:
    def is_healthy(self) -> bool:
        return False


class _OfflineAiAdapter:
    def is_healthy(self) -> bool:
        return False


def run_rehearsal() -> RehearsalEvidence:
    client = TestClient(app)

    previous_mode = os.environ.get("ANALYSIS_MODE")
    previous_guideline_url = os.environ.get("GUIDELINE_SERVICE_URL")
    previous_ai_url = os.environ.get("AI_SERVICE_URL")

    os.environ["ANALYSIS_MODE"] = "live"
    os.environ["GUIDELINE_SERVICE_URL"] = "https://offline-guideline.example"
    os.environ["AI_SERVICE_URL"] = "https://offline-ai.example"

    original_guideline_factory = analysis_engine._live_guideline_adapter_factory
    original_ai_factory = analysis_engine._live_ai_adapter_factory
    analysis_engine._live_guideline_adapter_factory = lambda _base_url: _OfflineGuidelineAdapter()
    analysis_engine._live_ai_adapter_factory = lambda _base_url: _OfflineAiAdapter()

    try:
        timings: dict[str, float] = {}

        started = time.perf_counter()
        analysis_response = client.post("/api/v1/orchestration/analysis/trigger", json={"patient_id": "PT-0001"})
        timings["analysis_trigger_seconds"] = round(time.perf_counter() - started, 4)
        analysis_response.raise_for_status()

        analysis = analysis_response.json()["analysis"]

        started = time.perf_counter()
        validate_response = client.post(
            f"/api/v1/orchestration/analysis/{analysis['analysis_id']}/validate",
            json={"confidence_threshold": 0.8, "actor": "rule-engine"},
        )
        timings["validation_seconds"] = round(time.perf_counter() - started, 4)
        validate_response.raise_for_status()

        started = time.perf_counter()
        decision_response = client.post(
            f"/api/v1/orchestration/runs/{analysis['run_id']}/decision",
            json={"decision": "approve", "actor": "coordinator-offline", "rationale": "Proceed"},
        )
        timings["decision_seconds"] = round(time.perf_counter() - started, 4)
        decision_response.raise_for_status()

        started = time.perf_counter()
        generate_response = client.post(
            f"/api/v1/orchestration/runs/{analysis['run_id']}/tasks/generate",
            json={"actor": "coordinator-offline"},
        )
        timings["task_generation_seconds"] = round(time.perf_counter() - started, 4)
        generate_response.raise_for_status()

        task_count = int(generate_response.json().get("created_count", 0))

        return RehearsalEvidence(
            dependency_state="offline",
            fallback_mode=str(analysis.get("adapter_mode", "unknown")),
            timings_seconds=timings,
            run_id=str(analysis.get("run_id", "")),
            analysis_id=str(analysis.get("analysis_id", "")),
            task_count=task_count,
        )
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


if __name__ == "__main__":
    evidence = run_rehearsal()
    print(json.dumps(asdict(evidence), indent=2, sort_keys=True))
