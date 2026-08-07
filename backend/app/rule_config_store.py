from __future__ import annotations

import logging
import os
from copy import deepcopy
from datetime import datetime, timezone


logger = logging.getLogger("care-orchestration-api")


class RuleConfigError(ValueError):
    """Raised when a rule configuration payload is invalid."""


DEFAULT_VERSION = "RULES-001"


def _default_rules() -> dict[str, object]:
    return {
        "version": DEFAULT_VERSION,
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
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _to_float(value: object, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RuleConfigError(f"{field_name} must be numeric") from exc


def _bounded_confidence(value: object, field_name: str) -> float:
    number = _to_float(value, field_name)
    if number <= 0 or number > 1:
        raise RuleConfigError(f"{field_name} must be between 0 and 1")
    return number


def validate_rule_payload(payload: dict[str, object]) -> dict[str, object]:
    """Validate and normalize a rule payload. Shared by all store backends."""
    if not isinstance(payload, dict):
        raise RuleConfigError("rule payload must be an object")

    version = str(payload.get("version", "")).strip()
    if not version:
        raise RuleConfigError("version is required")

    description = str(payload.get("description", "")).strip() or "Published rules"

    egfr_decline_threshold = _to_float(payload.get("egfr_decline_threshold"), "egfr_decline_threshold")
    if egfr_decline_threshold <= 0:
        raise RuleConfigError("egfr_decline_threshold must be greater than 0")

    uacr_missing_confidence = _bounded_confidence(payload.get("uacr_missing_confidence"), "uacr_missing_confidence")
    egfr_decline_confidence = _bounded_confidence(payload.get("egfr_decline_confidence"), "egfr_decline_confidence")
    high_risk_plan_confidence = _bounded_confidence(
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


class RuleConfigStore:
    """In-memory rule configuration store (default backend)."""

    def __init__(self) -> None:
        default_rules = _default_rules()
        self._versions: dict[str, dict[str, object]] = {DEFAULT_VERSION: default_rules}
        self._active_version = DEFAULT_VERSION

    def list_versions(self) -> list[dict[str, object]]:
        versions = [deepcopy(item) for item in self._versions.values()]
        versions.sort(key=lambda item: str(item.get("published_at_utc", "")), reverse=True)
        return versions

    def get_active_rules(self) -> dict[str, object]:
        active = self._versions[self._active_version]
        return deepcopy(active)

    def publish(self, payload: dict[str, object]) -> dict[str, object]:
        validated = validate_rule_payload(payload)
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

    # Retained for backwards compatibility with earlier callers/tests.
    def _validate(self, payload: dict[str, object]) -> dict[str, object]:
        return validate_rule_payload(payload)


class PostgresRuleConfigStore:
    """Postgres-backed rule configuration store.

    Mirrors :class:`RuleConfigStore` but persists versions and the active
    selection to Postgres so configuration survives restarts and is inspectable
    from pgAdmin.
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        from .db import ActiveRuleRow, RuleVersionRow

        with self._session_factory() as session:
            existing = session.get(RuleVersionRow, DEFAULT_VERSION)
            if existing is None:
                default_rules = _default_rules()
                session.add(
                    RuleVersionRow(
                        version=DEFAULT_VERSION,
                        published_at_utc=str(default_rules["published_at_utc"]),
                        payload=default_rules,
                    )
                )
            active = session.get(ActiveRuleRow, 1)
            if active is None:
                session.add(ActiveRuleRow(id=1, active_version=DEFAULT_VERSION))
            session.commit()

    def list_versions(self) -> list[dict[str, object]]:
        from .db import RuleVersionRow, select

        with self._session_factory() as session:
            rows = session.scalars(select(RuleVersionRow)).all()
            versions = [deepcopy(row.payload) for row in rows]
        versions.sort(key=lambda item: str(item.get("published_at_utc", "")), reverse=True)
        return versions

    def _active_version(self, session) -> str:
        from .db import ActiveRuleRow

        active = session.get(ActiveRuleRow, 1)
        return active.active_version if active else DEFAULT_VERSION

    def get_active_rules(self) -> dict[str, object]:
        from .db import RuleVersionRow

        with self._session_factory() as session:
            version = self._active_version(session)
            row = session.get(RuleVersionRow, version)
            if row is None:
                row = session.get(RuleVersionRow, DEFAULT_VERSION)
            if row is None:
                raise RuleConfigError("no active rule version available")
            return deepcopy(row.payload)

    def publish(self, payload: dict[str, object]) -> dict[str, object]:
        from .db import RuleVersionRow

        validated = validate_rule_payload(payload)
        version = validated["version"]
        with self._session_factory() as session:
            if session.get(RuleVersionRow, version) is not None:
                raise RuleConfigError(f"rule version '{version}' already exists")

            validated["published_at_utc"] = datetime.now(timezone.utc).isoformat()
            session.add(
                RuleVersionRow(
                    version=version,
                    published_at_utc=str(validated["published_at_utc"]),
                    payload=validated,
                )
            )
            session.commit()
        return deepcopy(validated)

    def activate(self, version: str) -> dict[str, object]:
        from .db import ActiveRuleRow, RuleVersionRow

        normalized = version.strip()
        if not normalized:
            raise RuleConfigError("version is required")

        with self._session_factory() as session:
            selected = session.get(RuleVersionRow, normalized)
            if selected is None:
                raise RuleConfigError(f"rule version '{normalized}' not found")

            active = session.get(ActiveRuleRow, 1)
            if active is None:
                session.add(ActiveRuleRow(id=1, active_version=normalized))
            else:
                active.active_version = normalized
            rules = deepcopy(selected.payload)
            session.commit()

        return {
            "active_version": normalized,
            "rules": rules,
        }


def _build_store():
    """Select a backend based on configuration, degrading safely to in-memory."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return RuleConfigStore()

    try:
        from .db import build_session_factory

        session_factory = build_session_factory()
        store = PostgresRuleConfigStore(session_factory)
        logger.info("rule_config_store: using Postgres backend")
        return store
    except Exception as exc:  # pragma: no cover - defensive startup fallback
        logger.warning(
            "rule_config_store: Postgres backend unavailable (%s); falling back to in-memory",
            exc,
        )
        return RuleConfigStore()


rule_config_store = _build_store()
