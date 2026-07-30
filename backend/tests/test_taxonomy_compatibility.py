from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _publish_taxonomy(version: str, compatible_from: list[str]) -> None:
    payload = {
        "version": version,
        "description": "Compatibility test taxonomy",
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
            "compatible_from": compatible_from,
            "migration_policy": "strict_additive",
        },
    }
    response = client.post("/api/v1/orchestration/taxonomy/publish", json=payload)
    assert response.status_code == 200


def _activate_taxonomy(version: str) -> None:
    response = client.post(
        "/api/v1/orchestration/taxonomy/activate",
        json={"version": version, "actor": "qa"},
    )
    assert response.status_code == 200


def _valid_gap_payload() -> list[dict[str, object]]:
    return [
        {
            "gap_id": "GAP-UACR-MISSING",
            "recommendation_id": "REC-UACR-001",
            "title": "Order UACR Test",
            "reasoning": "Missing UACR",
            "evidence": [{"code": "KDIGO-1"}],
            "confidence": 0.92,
            "severity": "high",
        }
    ]


def test_nonconforming_payload_rejected_with_explicit_error() -> None:
    invalid_gaps = [{"gap_id": "GAP-UACR-MISSING", "confidence": 0.9}]

    response = client.post(
        "/api/v1/orchestration/taxonomy/validate",
        json={"gaps": invalid_gaps},
    )
    assert response.status_code == 400
    assert "missing required fields" in response.json()["detail"]


def test_version_registry_and_compatibility_metadata_stored() -> None:
    new_version = f"TAX-REG-{uuid4()}"
    _publish_taxonomy(version=new_version, compatible_from=["TAX-1.0"])

    versions_response = client.get("/api/v1/orchestration/taxonomy/versions")
    assert versions_response.status_code == 200
    payload = versions_response.json()

    match = next(item for item in payload["versions"] if item["version"] == new_version)
    assert match["compatibility"]["compatible_from"] == ["TAX-1.0"]
    assert match["compatibility"]["migration_policy"] == "strict_additive"


def test_migration_compatibility_scenarios() -> None:
    source_version = "TAX-1.0"
    target_version = f"TAX-MIG-{uuid4()}"
    _publish_taxonomy(version=target_version, compatible_from=[source_version])

    compatibility_ok = client.post(
        "/api/v1/orchestration/taxonomy/compatibility/check",
        json={
            "source_version": source_version,
            "target_version": target_version,
            "gaps": _valid_gap_payload(),
        },
    )
    assert compatibility_ok.status_code == 200
    assert compatibility_ok.json()["is_compatible"] is True

    incompatible_target = f"TAX-MIG-NO-{uuid4()}"
    _publish_taxonomy(version=incompatible_target, compatible_from=["TAX-0.9"])

    compatibility_no = client.post(
        "/api/v1/orchestration/taxonomy/compatibility/check",
        json={
            "source_version": source_version,
            "target_version": incompatible_target,
            "gaps": _valid_gap_payload(),
        },
    )
    assert compatibility_no.status_code == 200
    assert compatibility_no.json()["is_compatible"] is False


def test_next_analysis_uses_active_taxonomy_version_without_redeploy() -> None:
    baseline = client.get("/api/v1/orchestration/taxonomy/active")
    assert baseline.status_code == 200
    baseline_version = baseline.json()["active_version"]

    new_version = f"TAX-ACT-{uuid4()}"
    _publish_taxonomy(version=new_version, compatible_from=[baseline_version])
    _activate_taxonomy(new_version)

    try:
        analysis_response = client.post(
            "/api/v1/orchestration/analysis/trigger",
            json={"patient_id": "PT-0001"},
        )
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()["analysis"]
        assert analysis["taxonomy_version"] == new_version
    finally:
        _activate_taxonomy(baseline_version)
