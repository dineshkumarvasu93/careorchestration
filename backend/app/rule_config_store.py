from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone


class RuleConfigError(ValueError):
    """Raised when a rule configuration payload is invalid."""


class RuleConfigStore:
    def __init__(self) -> None:
        default_version = "RULES-001"
        now_utc = datetime.now(timezone.utc).isoformat()
        default_rules = {
            "version": default_version,
            "description": "Baseline deterministic CKD rules",
            "egfr_decline_threshold": 8.0,
            "uacr_missing_confidence": 0.92,
            "egfr_decline_confidence": 0.88,
            "high_risk_plan_confidence": 0.9,
            "include_high_risk_plan": True,
            "known_gap_ids": [
                "GAP-UACR-MISSING",
                "GAP-EGFR-DECLINE",
                "GAP-CKD-HIGH-RISK-PLAN",
                "GAP-NO-ACTION",
            ],
            "published_at_utc": now_utc,
        }
        self._versions: dict[str, dict[str, object]] = {default_version: default_rules}
        self._active_version = default_version

    def list_versions(self) -> list[dict[str, object]]:
        versions = [deepcopy(item) for item in self._versions.values()]
        versions.sort(key=lambda item: str(item.get("published_at_utc", "")), reverse=True)
        return versions

    def get_active_rules(self) -> dict[str, object]:
        active = self._versions[self._active_version]
        return deepcopy(active)

    def publish(self, payload: dict[str, object]) -> dict[str, object]:
        validated = self._validate(payload)
        version = validated["version"]
        if version in self._versions:
            raise RuleConfigError(f"rule version '{version}' already exists")

        validated["published_at_utc"] = datetime.now(timezone.utc).isoformat()
        self._versions[version] = validated
        return deepcopy(validated)

    def activate(self, version: str) -> dict[str, object]:
        normalized = version.strip()
        if not normalized:
            raise RuleConfigError("version is required")

        selected = self._versions.get(normalized)
        if not selected:
            raise RuleConfigError(f"rule version '{normalized}' not found")

        self._active_version = normalized
        return {
            "active_version": self._active_version,
            "rules": deepcopy(selected),
        }

    def _validate(self, payload: dict[str, object]) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise RuleConfigError("rule payload must be an object")

        version = str(payload.get("version", "")).strip()
        if not version:
            raise RuleConfigError("version is required")

        description = str(payload.get("description", "")).strip() or "Published rules"

        egfr_decline_threshold = self._to_float(payload.get("egfr_decline_threshold"), "egfr_decline_threshold")
        if egfr_decline_threshold <= 0:
            raise RuleConfigError("egfr_decline_threshold must be greater than 0")

        uacr_missing_confidence = self._bounded_confidence(payload.get("uacr_missing_confidence"), "uacr_missing_confidence")
        egfr_decline_confidence = self._bounded_confidence(payload.get("egfr_decline_confidence"), "egfr_decline_confidence")
        high_risk_plan_confidence = self._bounded_confidence(
            payload.get("high_risk_plan_confidence"),
            "high_risk_plan_confidence",
        )

        include_high_risk_plan = payload.get("include_high_risk_plan")
        if not isinstance(include_high_risk_plan, bool):
            raise RuleConfigError("include_high_risk_plan must be boolean")

        known_gap_ids = payload.get("known_gap_ids")
        if not isinstance(known_gap_ids, list) or not known_gap_ids:
            raise RuleConfigError("known_gap_ids must be a non-empty array")

        normalized_gap_ids: list[str] = []
        for gap_id in known_gap_ids:
            text = str(gap_id).strip()
            if not text:
                raise RuleConfigError("known_gap_ids cannot include empty values")
            normalized_gap_ids.append(text)

        if "GAP-NO-ACTION" not in normalized_gap_ids:
            raise RuleConfigError("known_gap_ids must include GAP-NO-ACTION")

        return {
            "version": version,
            "description": description,
            "egfr_decline_threshold": egfr_decline_threshold,
            "uacr_missing_confidence": uacr_missing_confidence,
            "egfr_decline_confidence": egfr_decline_confidence,
            "high_risk_plan_confidence": high_risk_plan_confidence,
            "include_high_risk_plan": include_high_risk_plan,
            "known_gap_ids": normalized_gap_ids,
        }

    def _to_float(self, value: object, field_name: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise RuleConfigError(f"{field_name} must be numeric") from exc

    def _bounded_confidence(self, value: object, field_name: str) -> float:
        number = self._to_float(value, field_name)
        if number <= 0 or number > 1:
            raise RuleConfigError(f"{field_name} must be between 0 and 1")
        return number


rule_config_store = RuleConfigStore()
