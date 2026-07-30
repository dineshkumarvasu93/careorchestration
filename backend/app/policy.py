from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

PROTOTYPE_DISCLAIMER = (
    "Prototype only. Synthetic data only. Not clinical decision support and not for patient care decisions."
)


@dataclass(frozen=True)
class PolicyAuditEvent:
    event_id: int
    timestamp_utc: str
    event_type: str
    action: str
    actor: str
    channel: str
    reason: str
    run_id: str | None
    patient_id: str | None
    payload_hash: str
    previous_hash: str
    current_hash: str
    details: dict[str, Any]


class PolicyAuditLog:
    def __init__(self) -> None:
        self._events: list[PolicyAuditEvent] = []

    def record(self, event_type: str, action: str, reason: str, details: dict[str, Any]) -> None:
        safe_details = details if isinstance(details, dict) else {}
        actor = str(safe_details.get("actor", "system")).strip() or "system"
        channel = str(safe_details.get("channel", "api")).strip() or "api"
        run_id = self._string_or_none(safe_details.get("run_id"))
        patient_id = self._string_or_none(safe_details.get("patient_id"))

        event_id = len(self._events) + 1
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        payload_hash = self._hash_payload(
            {
                "event_id": event_id,
                "timestamp_utc": timestamp_utc,
                "event_type": event_type,
                "action": action,
                "actor": actor,
                "channel": channel,
                "reason": reason,
                "run_id": run_id,
                "patient_id": patient_id,
                "details": safe_details,
            }
        )
        previous_hash = self._events[-1].current_hash if self._events else "GENESIS"
        current_hash = self._hash_payload(
            {
                "previous_hash": previous_hash,
                "payload_hash": payload_hash,
            }
        )

        event = PolicyAuditEvent(
            event_id=event_id,
            timestamp_utc=timestamp_utc,
            event_type=event_type,
            action=action,
            actor=actor,
            channel=channel,
            reason=reason,
            run_id=run_id,
            patient_id=patient_id,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
            current_hash=current_hash,
            details=safe_details,
        )
        self._events.append(event)

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 500))
        selected = self._events[-bounded_limit:]
        return [
            {
                "event_id": event.event_id,
                "timestamp_utc": event.timestamp_utc,
                "event_type": event.event_type,
                "action": event.action,
                "actor": event.actor,
                "channel": event.channel,
                "reason": event.reason,
                "run_id": event.run_id,
                "patient_id": event.patient_id,
                "payload_hash": event.payload_hash,
                "previous_hash": event.previous_hash,
                "current_hash": event.current_hash,
                "details": event.details,
            }
            for event in selected
        ]

    def verify_integrity(self) -> dict[str, Any]:
        failures: list[dict[str, Any]] = []
        previous_hash = "GENESIS"

        for event in self._events:
            expected_payload_hash = self._hash_payload(
                {
                    "event_id": event.event_id,
                    "timestamp_utc": event.timestamp_utc,
                    "event_type": event.event_type,
                    "action": event.action,
                    "actor": event.actor,
                    "channel": event.channel,
                    "reason": event.reason,
                    "run_id": event.run_id,
                    "patient_id": event.patient_id,
                    "details": event.details,
                }
            )
            if event.payload_hash != expected_payload_hash:
                failures.append(
                    {
                        "event_id": event.event_id,
                        "error": "payload_hash_mismatch",
                    }
                )

            if event.previous_hash != previous_hash:
                failures.append(
                    {
                        "event_id": event.event_id,
                        "error": "previous_hash_mismatch",
                    }
                )

            expected_current_hash = self._hash_payload(
                {
                    "previous_hash": event.previous_hash,
                    "payload_hash": event.payload_hash,
                }
            )
            if event.current_hash != expected_current_hash:
                failures.append(
                    {
                        "event_id": event.event_id,
                        "error": "current_hash_mismatch",
                    }
                )

            previous_hash = event.current_hash

        return {
            "event_count": len(self._events),
            "is_valid": len(failures) == 0,
            "failures": failures,
        }

    def get_patient_timeline(self, patient_id: str, limit: int = 500) -> dict[str, Any]:
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            return {
                "patient_id": "",
                "count": 0,
                "events": [],
            }

        run_to_patient: dict[str, str] = {}
        for event in self._events:
            if event.run_id and event.patient_id:
                run_to_patient[event.run_id] = event.patient_id

        matching_events: list[dict[str, Any]] = []
        for event in self._events:
            matched = False
            if event.patient_id == normalized_patient_id:
                matched = True
            elif event.run_id and run_to_patient.get(event.run_id) == normalized_patient_id:
                matched = True

            if matched:
                matching_events.append(
                    {
                        "event_id": event.event_id,
                        "timestamp_utc": event.timestamp_utc,
                        "event_type": event.event_type,
                        "action": event.action,
                        "actor": event.actor,
                        "channel": event.channel,
                        "reason": event.reason,
                        "run_id": event.run_id,
                        "patient_id": event.patient_id,
                        "payload_hash": event.payload_hash,
                        "previous_hash": event.previous_hash,
                        "current_hash": event.current_hash,
                        "details": event.details,
                    }
                )

        bounded_limit = max(1, min(limit, 1000))
        selected = matching_events[-bounded_limit:]
        return {
            "patient_id": normalized_patient_id,
            "count": len(selected),
            "events": selected,
        }

    def _hash_payload(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


policy_audit_log = PolicyAuditLog()
