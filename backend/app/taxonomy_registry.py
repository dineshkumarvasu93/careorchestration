from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone


class TaxonomyError(ValueError):
    """Raised when taxonomy payloads or compatibility checks fail."""


class TaxonomyRegistry:
    def __init__(self) -> None:
        now_utc = datetime.now(timezone.utc).isoformat()
        baseline_version = "TAX-1.0"
        baseline = {
            "version": baseline_version,
            "description": "Baseline care-gap taxonomy",
            "schema": {
                "required_gap_fields": [
                    "gap_id",
                    "recommendation_id",
                    "title",
                    "reasoning",
                    "evidence",
                    "confidence",
                    "severity",
                ],
                "allowed_severity": ["low", "moderate", "high"],
            },
            "compatibility": {
                "compatible_from": [baseline_version],
                "migration_policy": "strict_additive",
            },
            "published_at_utc": now_utc,
        }

        self._versions: dict[str, dict[str, object]] = {baseline_version: baseline}
        self._active_version = baseline_version

    def list_versions(self) -> list[dict[str, object]]:
        versions = [deepcopy(item) for item in self._versions.values()]
        versions.sort(key=lambda item: str(item.get("published_at_utc", "")), reverse=True)
        return versions

    def get_active(self) -> dict[str, object]:
        return deepcopy(self._versions[self._active_version])

    def publish(self, payload: dict[str, object]) -> dict[str, object]:
        validated = self._validate_version_payload(payload)
        version = str(validated["version"])
        if version in self._versions:
            raise TaxonomyError(f"taxonomy version '{version}' already exists")

        validated["published_at_utc"] = datetime.now(timezone.utc).isoformat()
        self._versions[version] = validated
        return deepcopy(validated)

    def activate(self, version: str) -> dict[str, object]:
        normalized = version.strip()
        if not normalized:
            raise TaxonomyError("version is required")

        selected = self._versions.get(normalized)
        if not selected:
            raise TaxonomyError(f"taxonomy version '{normalized}' not found")

        self._active_version = normalized
        return {
            "active_version": normalized,
            "taxonomy": deepcopy(selected),
        }

    def validate_gaps(self, gaps: object, taxonomy_version: str | None = None) -> dict[str, object]:
        taxonomy = self._resolve_taxonomy(taxonomy_version)

        if not isinstance(gaps, list):
            raise TaxonomyError("gaps must be a list")

        schema = taxonomy.get("schema", {}) if isinstance(taxonomy, dict) else {}
        required_fields = schema.get("required_gap_fields", []) if isinstance(schema, dict) else []
        allowed_severity = set(schema.get("allowed_severity", [])) if isinstance(schema, dict) else set()

        if not isinstance(required_fields, list) or not required_fields:
            raise TaxonomyError("taxonomy schema is missing required_gap_fields")

        for index, gap in enumerate(gaps):
            if not isinstance(gap, dict):
                raise TaxonomyError(f"gap[{index}] must be an object")

            missing = [field for field in required_fields if field not in gap]
            if missing:
                raise TaxonomyError(f"gap[{index}] missing required fields: {missing}")

            severity = str(gap.get("severity", "")).strip().lower()
            if allowed_severity and severity not in allowed_severity:
                raise TaxonomyError(
                    f"gap[{index}].severity '{severity}' is invalid. Allowed: {sorted(allowed_severity)}"
                )

            confidence_raw = gap.get("confidence")
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError) as exc:
                raise TaxonomyError(f"gap[{index}].confidence must be numeric") from exc
            if confidence < 0 or confidence > 1:
                raise TaxonomyError(f"gap[{index}].confidence must be between 0 and 1")

        return {
            "taxonomy_version": str(taxonomy.get("version", "unknown")),
            "validated_count": len(gaps),
        }

    def check_compatibility(
        self,
        source_version: str,
        target_version: str,
        gaps: object,
    ) -> dict[str, object]:
        source = self._resolve_taxonomy(source_version)
        target = self._resolve_taxonomy(target_version)

        source_name = str(source.get("version", ""))
        target_name = str(target.get("version", ""))
        compatibility = target.get("compatibility", {}) if isinstance(target, dict) else {}
        compatible_from = compatibility.get("compatible_from", []) if isinstance(compatibility, dict) else []

        if not isinstance(compatible_from, list):
            compatible_from = []

        if source_name not in {str(item) for item in compatible_from}:
            return {
                "source_version": source_name,
                "target_version": target_name,
                "is_compatible": False,
                "reason": f"target taxonomy does not declare compatibility from '{source_name}'",
            }

        validation = self.validate_gaps(gaps=gaps, taxonomy_version=target_name)
        return {
            "source_version": source_name,
            "target_version": target_name,
            "is_compatible": True,
            "reason": "compatible_by_declared_policy",
            "validated_count": validation["validated_count"],
        }

    def _resolve_taxonomy(self, version: str | None) -> dict[str, object]:
        if version is None or not version.strip():
            return self.get_active()

        selected = self._versions.get(version.strip())
        if not selected:
            raise TaxonomyError(f"taxonomy version '{version.strip()}' not found")

        return deepcopy(selected)

    def _validate_version_payload(self, payload: dict[str, object]) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise TaxonomyError("taxonomy payload must be an object")

        version = str(payload.get("version", "")).strip()
        if not version:
            raise TaxonomyError("version is required")

        description = str(payload.get("description", "")).strip() or "Published taxonomy version"

        schema = payload.get("schema")
        if not isinstance(schema, dict):
            raise TaxonomyError("schema must be an object")

        required_gap_fields = schema.get("required_gap_fields")
        if not isinstance(required_gap_fields, list) or not required_gap_fields:
            raise TaxonomyError("schema.required_gap_fields must be a non-empty array")

        normalized_fields: list[str] = []
        for field_name in required_gap_fields:
            text = str(field_name).strip()
            if not text:
                raise TaxonomyError("schema.required_gap_fields cannot contain empty field names")
            normalized_fields.append(text)

        expected_baseline = {
            "gap_id",
            "recommendation_id",
            "title",
            "reasoning",
            "evidence",
            "confidence",
            "severity",
        }
        if not expected_baseline.issubset(set(normalized_fields)):
            raise TaxonomyError(
                "schema.required_gap_fields must include baseline contract fields"
            )

        allowed_severity = schema.get("allowed_severity")
        if not isinstance(allowed_severity, list) or not allowed_severity:
            raise TaxonomyError("schema.allowed_severity must be a non-empty array")

        normalized_severity = [str(item).strip().lower() for item in allowed_severity if str(item).strip()]
        if not normalized_severity:
            raise TaxonomyError("schema.allowed_severity cannot be empty")

        compatibility = payload.get("compatibility")
        if not isinstance(compatibility, dict):
            raise TaxonomyError("compatibility must be an object")

        compatible_from = compatibility.get("compatible_from")
        if not isinstance(compatible_from, list) or not compatible_from:
            raise TaxonomyError("compatibility.compatible_from must be a non-empty array")

        normalized_compatible_from = [str(item).strip() for item in compatible_from if str(item).strip()]
        if not normalized_compatible_from:
            raise TaxonomyError("compatibility.compatible_from cannot be empty")

        migration_policy = str(compatibility.get("migration_policy", "")).strip()
        if not migration_policy:
            raise TaxonomyError("compatibility.migration_policy is required")

        return {
            "version": version,
            "description": description,
            "schema": {
                "required_gap_fields": normalized_fields,
                "allowed_severity": normalized_severity,
            },
            "compatibility": {
                "compatible_from": normalized_compatible_from,
                "migration_policy": migration_policy,
            },
        }


taxonomy_registry = TaxonomyRegistry()
