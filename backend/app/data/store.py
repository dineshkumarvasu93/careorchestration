from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..policy import policy_audit_log


class SeedDataError(ValueError):
    """Raised when fixture data is missing or invalid."""


@dataclass(frozen=True)
class PatientRecord:
    patient_id: str
    is_synthetic: bool
    demographics: dict[str, Any]
    ckd_stage: str
    egfr: dict[str, Any]
    uacr: dict[str, Any]
    medication_summary: list[str]
    last_nephrology_visit_date: str


class PatientStore:
    """In-memory store seeded from synthetic fixture files."""

    def __init__(self) -> None:
        self._records_by_id: dict[str, PatientRecord] = {}
        self._quarantined_records: list[dict[str, Any]] = []

    @property
    def count(self) -> int:
        return len(self._records_by_id)

    @property
    def quarantined_count(self) -> int:
        return len(self._quarantined_records)

    def load_from_file(self, file_path: Path) -> None:
        if not file_path.exists():
            raise SeedDataError(f"Fixture file not found: {file_path}")

        payload = json.loads(file_path.read_text(encoding="utf-8"))
        records = payload.get("patients", [])
        if not isinstance(records, list) or not records:
            raise SeedDataError("Fixture payload must include non-empty 'patients' array")

        next_records: dict[str, PatientRecord] = {}
        for item in records:
            try:
                record = self._validate_and_parse(item)
            except SeedDataError as exc:
                item_patient_id = item.get("patient_id", "unknown") if isinstance(item, dict) else "unknown"
                self._quarantined_records.append(
                    {
                        "patient_id": item_patient_id,
                        "reason": str(exc),
                        "source": "seed_fixture",
                    }
                )
                policy_audit_log.record(
                    event_type="synthetic_policy",
                    action="quarantined",
                    reason="seed_fixture_nonconforming_record",
                    details={"patient_id": item_patient_id, "error": str(exc)},
                )
                continue

            next_records[record.patient_id] = record

        if not next_records:
            raise SeedDataError("No valid synthetic patient records available after policy checks")

        # Idempotent load: replace current map with latest validated fixture snapshot.
        self._records_by_id = next_records

    def search(self, query: str) -> list[dict[str, str]]:
        query_text = query.strip().lower()
        if not query_text:
            return []

        matches: list[dict[str, str]] = []
        for record in self._records_by_id.values():
            full_name = (
                f"{record.demographics.get('first_name', '')} "
                f"{record.demographics.get('last_name', '')}"
            ).strip()
            haystack = " ".join(
                [
                    record.patient_id,
                    record.demographics.get("first_name", ""),
                    record.demographics.get("last_name", ""),
                    full_name,
                    record.ckd_stage,
                ]
            ).lower()
            if query_text in haystack:
                matches.append(
                    {
                        "patient_id": record.patient_id,
                        "name": full_name,
                        "ckd_stage": record.ckd_stage,
                    }
                )

        return matches

    def get_profile(self, patient_id: str) -> dict[str, Any] | None:
        record = self._records_by_id.get(patient_id)
        if not record:
            return None

        return {
            "patient_id": record.patient_id,
            "is_synthetic": record.is_synthetic,
            "demographics": record.demographics,
            "ckd_stage": record.ckd_stage,
            "egfr": record.egfr,
            "uacr": record.uacr,
            "medication_summary": record.medication_summary,
            "last_nephrology_visit_date": record.last_nephrology_visit_date,
        }

    def get_quarantined_records(self) -> list[dict[str, Any]]:
        return list(self._quarantined_records)

    def ingest_records(
        self,
        records: list[dict[str, Any]],
        mode: str,
        actor: str,
    ) -> dict[str, object]:
        if mode not in {"reject", "quarantine"}:
            raise SeedDataError("mode must be either 'reject' or 'quarantine'")

        accepted: list[dict[str, str]] = []
        blocked: list[dict[str, str]] = []

        for item in records:
            try:
                record = self._validate_and_parse(item)
            except SeedDataError as exc:
                patient_id = item.get("patient_id", "unknown") if isinstance(item, dict) else "unknown"
                action = "quarantined" if mode == "quarantine" else "rejected"

                if mode == "quarantine":
                    self._quarantined_records.append(
                        {
                            "patient_id": patient_id,
                            "reason": str(exc),
                            "source": "ingestion",
                        }
                    )

                blocked.append({"patient_id": patient_id, "reason": str(exc), "action": action})
                policy_audit_log.record(
                    event_type="synthetic_policy",
                    action=action,
                    reason="ingestion_nonconforming_record",
                    details={"patient_id": patient_id, "actor": actor, "error": str(exc)},
                )
                continue

            self._records_by_id[record.patient_id] = record
            accepted.append({"patient_id": record.patient_id})
            policy_audit_log.record(
                event_type="synthetic_policy",
                action="accepted",
                reason="ingestion_conforming_record",
                details={"patient_id": record.patient_id, "actor": actor},
            )

        return {
            "mode": mode,
            "accepted_count": len(accepted),
            "blocked_count": len(blocked),
            "accepted": accepted,
            "blocked": blocked,
            "quarantined_total": self.quarantined_count,
        }

    def _validate_and_parse(self, item: dict[str, Any]) -> PatientRecord:
        if not isinstance(item, dict):
            raise SeedDataError("Patient record payload must be an object")

        required_fields = [
            "patient_id",
            "is_synthetic",
            "demographics",
            "ckd_stage",
            "egfr",
            "uacr",
            "medication_summary",
            "last_nephrology_visit_date",
        ]
        missing = [field for field in required_fields if field not in item]
        if missing:
            raise SeedDataError(f"Patient record missing fields: {missing}")

        if item["is_synthetic"] is not True:
            raise SeedDataError(
                f"Patient '{item.get('patient_id', 'unknown')}' is not marked synthetic"
            )

        demographics = item["demographics"]
        for field in ["first_name", "last_name", "age", "gender"]:
            if field not in demographics:
                raise SeedDataError(
                    f"Patient '{item['patient_id']}' missing demographics.{field}"
                )

        return PatientRecord(
            patient_id=str(item["patient_id"]),
            is_synthetic=bool(item["is_synthetic"]),
            demographics=demographics,
            ckd_stage=str(item["ckd_stage"]),
            egfr=item["egfr"],
            uacr=item["uacr"],
            medication_summary=list(item["medication_summary"]),
            last_nephrology_visit_date=str(item["last_nephrology_visit_date"]),
        )


patient_store = PatientStore()
