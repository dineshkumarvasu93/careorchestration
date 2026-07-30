from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib import error, request
from uuid import uuid4

from .rule_config_store import rule_config_store
from .taxonomy_registry import taxonomy_registry


class GuidelineAdapter:
    """Deterministic guideline context adapter for prototype analysis."""

    def get_context(self, profile: dict[str, object]) -> list[dict[str, str]]:
        return [
            {
                "code": "KDIGO-CKD-UACR-TESTING",
                "statement": "Patients with CKD require periodic UACR testing for risk stratification.",
            },
            {
                "code": "KDIGO-CKD-NEPHROLOGY-REFERRAL",
                "statement": "Declining eGFR with progression risk should prompt nephrology follow-up.",
            },
        ]


class AiRecommendationAdapter:
    """Deterministic recommendation adapter used in mock-mode prototype."""

    def generate(
        self,
        profile: dict[str, object],
        guideline_context: list[dict[str, str]],
        rule_config: dict[str, object],
    ) -> dict[str, object]:
        egfr = profile.get("egfr", {}) if isinstance(profile.get("egfr", {}), dict) else {}
        uacr = profile.get("uacr", {}) if isinstance(profile.get("uacr", {}), dict) else {}

        current_egfr = float(egfr.get("current", 0)) if egfr.get("current") is not None else 0.0
        previous_egfr = float(egfr.get("previous", 0)) if egfr.get("previous") is not None else 0.0
        egfr_delta = previous_egfr - current_egfr
        uacr_status = str(uacr.get("status", "missing"))

        egfr_decline_threshold = float(rule_config.get("egfr_decline_threshold", 8.0))
        uacr_missing_confidence = float(rule_config.get("uacr_missing_confidence", 0.92))
        egfr_decline_confidence = float(rule_config.get("egfr_decline_confidence", 0.88))
        high_risk_plan_confidence = float(rule_config.get("high_risk_plan_confidence", 0.9))
        include_high_risk_plan = bool(rule_config.get("include_high_risk_plan", True))

        gaps: list[dict[str, object]] = []

        if uacr_status == "missing":
            gaps.append(
                {
                    "gap_id": "GAP-UACR-MISSING",
                    "recommendation_id": "REC-UACR-001",
                    "title": "Order UACR Test",
                    "reasoning": "UACR status is missing, so albuminuria risk cannot be stratified.",
                    "evidence": [guideline_context[0]],
                    "confidence": uacr_missing_confidence,
                    "severity": "high",
                }
            )

        if egfr_delta >= egfr_decline_threshold:
            gaps.append(
                {
                    "gap_id": "GAP-EGFR-DECLINE",
                    "recommendation_id": "REC-NEPH-002",
                    "title": "Schedule Nephrology Follow-up",
                    "reasoning": "eGFR decline exceeds trend threshold and requires specialist follow-up.",
                    "evidence": [guideline_context[1]],
                    "confidence": egfr_decline_confidence,
                    "severity": "high",
                }
            )

        if include_high_risk_plan and uacr_status == "missing" and egfr_delta >= egfr_decline_threshold:
            gaps.append(
                {
                    "gap_id": "GAP-CKD-HIGH-RISK-PLAN",
                    "recommendation_id": "REC-CKD-003",
                    "title": "Initiate High-Risk CKD Follow-up Plan",
                    "reasoning": "Combined missing UACR and rapid eGFR decline requires accelerated follow-up planning.",
                    "evidence": guideline_context,
                    "confidence": high_risk_plan_confidence,
                    "severity": "high",
                }
            )

        if not gaps:
            gaps.append(
                {
                    "gap_id": "GAP-NO-ACTION",
                    "recommendation_id": "REC-MONITOR-003",
                    "title": "Continue Routine Monitoring",
                    "reasoning": "No immediate high-risk gap detected from current synthetic profile.",
                    "evidence": [guideline_context[0]],
                    "confidence": 0.74,
                    "severity": "low",
                }
            )

        confidence = round(sum(float(gap["confidence"]) for gap in gaps) / len(gaps), 2)
        risk_level = "high" if any(gap["severity"] == "high" for gap in gaps) else "moderate"

        return {
            "risk_level": risk_level,
            "confidence": confidence,
            "gaps": gaps,
            "reasoning": "Analysis generated from synthetic patient context and deterministic guideline mapping.",
            "evidence": guideline_context,
            "triggered_at_utc": datetime.now(timezone.utc).isoformat(),
        }


class LiveGuidelineAdapter:
    """Guideline context adapter that reads from external service in live mode."""

    def __init__(self, base_url: str, timeout_seconds: float = 2.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def is_healthy(self) -> bool:
        if not self._base_url:
            return False

        try:
            status_code, _ = self._http_get_json(f"{self._base_url}/health")
            return status_code == 200
        except (error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return False

    def get_context(self, profile: dict[str, object]) -> list[dict[str, str]]:
        if not self._base_url:
            raise ValueError("guideline service URL is not configured")

        status_code, payload = self._http_post_json(
            f"{self._base_url}/context",
            {"profile": profile},
        )
        if status_code != 200:
            raise ValueError("guideline service context request failed")

        context = payload.get("context", [])
        if not isinstance(context, list):
            raise ValueError("guideline context payload is invalid")

        normalized: list[dict[str, str]] = []
        for item in context:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "code": str(item.get("code", "UNKNOWN")),
                    "statement": str(item.get("statement", "")),
                }
            )
        if not normalized:
            raise ValueError("guideline context payload is empty")

        return normalized

    def _http_get_json(self, url: str) -> tuple[int, dict[str, object]]:
        req = request.Request(url=url, method="GET")
        with request.urlopen(req, timeout=self._timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError("response payload must be an object")
            return int(response.status), payload

    def _http_post_json(self, url: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            method="POST",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=self._timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            response_payload = json.loads(body)
            if not isinstance(response_payload, dict):
                raise ValueError("response payload must be an object")
            return int(response.status), response_payload


class LiveAiRecommendationAdapter:
    """AI recommendation adapter that reads from external service in live mode."""

    def __init__(self, base_url: str, timeout_seconds: float = 2.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def is_healthy(self) -> bool:
        if not self._base_url:
            return False

        try:
            status_code, _ = self._http_get_json(f"{self._base_url}/health")
            return status_code == 200
        except (error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return False

    def generate(
        self,
        profile: dict[str, object],
        guideline_context: list[dict[str, str]],
    ) -> dict[str, object]:
        if not self._base_url:
            raise ValueError("ai service URL is not configured")

        status_code, payload = self._http_post_json(
            f"{self._base_url}/recommendations",
            {
                "profile": profile,
                "guideline_context": guideline_context,
            },
        )
        if status_code != 200:
            raise ValueError("ai service recommendation request failed")

        for required in ["risk_level", "confidence", "gaps", "reasoning", "evidence"]:
            if required not in payload:
                raise ValueError(f"ai response missing '{required}'")

        if not isinstance(payload.get("gaps"), list):
            raise ValueError("ai response gaps must be a list")

        if "triggered_at_utc" not in payload:
            payload["triggered_at_utc"] = datetime.now(timezone.utc).isoformat()

        return payload

    def _http_get_json(self, url: str) -> tuple[int, dict[str, object]]:
        req = request.Request(url=url, method="GET")
        with request.urlopen(req, timeout=self._timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError("response payload must be an object")
            return int(response.status), payload

    def _http_post_json(self, url: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            method="POST",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=self._timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            response_payload = json.loads(body)
            if not isinstance(response_payload, dict):
                raise ValueError("response payload must be an object")
            return int(response.status), response_payload


class AnalysisEngine:
    def __init__(self) -> None:
        self._guideline_adapter = GuidelineAdapter()
        self._ai_adapter = AiRecommendationAdapter()
        self._live_guideline_adapter_factory = lambda base_url: LiveGuidelineAdapter(base_url=base_url)
        self._live_ai_adapter_factory = lambda base_url: LiveAiRecommendationAdapter(base_url=base_url)

    def analyze(self, patient_id: str, profile: dict[str, object]) -> dict[str, object]:
        rule_config = rule_config_store.get_active_rules()
        active_taxonomy = taxonomy_registry.get_active()
        adapter_mode, guideline_context, ai_result = self._analyze_with_mode(
            profile=profile,
            rule_config=rule_config,
        )

        return {
            "analysis_id": f"AN-{uuid4()}",
            "patient_id": patient_id,
            "risk": ai_result["risk_level"],
            "confidence": ai_result["confidence"],
            "gaps": ai_result["gaps"],
            "reasoning": ai_result["reasoning"],
            "evidence": ai_result["evidence"],
            "triggered_at_utc": ai_result["triggered_at_utc"],
            "status": "completed",
            "traceability": "TR-003",
            "adapter_mode": adapter_mode,
            "rule_version": str(rule_config.get("version", "unknown")),
            "taxonomy_version": str(active_taxonomy.get("version", "unknown")),
            "taxonomy_compatibility": dict(active_taxonomy.get("compatibility", {})),
        }

    def _analyze_with_mode(
        self,
        profile: dict[str, object],
        rule_config: dict[str, object],
    ) -> tuple[str, list[dict[str, str]], dict[str, object]]:
        configured_mode = os.getenv("ANALYSIS_MODE", "mock").strip().lower() or "mock"
        guideline_service_url = os.getenv("GUIDELINE_SERVICE_URL", "").strip()
        ai_service_url = os.getenv("AI_SERVICE_URL", "").strip()

        if configured_mode == "live":
            live_guideline_adapter = self._live_guideline_adapter_factory(guideline_service_url)
            live_ai_adapter = self._live_ai_adapter_factory(ai_service_url)
            if live_guideline_adapter.is_healthy() and live_ai_adapter.is_healthy():
                try:
                    guideline_context = live_guideline_adapter.get_context(profile)
                    ai_result = live_ai_adapter.generate(
                        profile=profile,
                        guideline_context=guideline_context,
                    )
                    return "live", guideline_context, ai_result
                except (error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
                    # Fall back to deterministic mode to keep orchestration available.
                    pass

        guideline_context = self._guideline_adapter.get_context(profile)
        ai_result = self._ai_adapter.generate(
            profile=profile,
            guideline_context=guideline_context,
            rule_config=rule_config,
        )
        return "mock", guideline_context, ai_result


analysis_engine = AnalysisEngine()
