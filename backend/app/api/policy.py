from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..policy import PROTOTYPE_DISCLAIMER, policy_audit_log

router = APIRouter(prefix="/api/v1/policy", tags=["policy"])


@router.get("/disclaimer")
def get_disclaimer(channel: str = Query(default="ui", min_length=2, max_length=30)) -> dict[str, str]:
    normalized_channel = channel.strip().lower() or "ui"
    policy_audit_log.record(
        event_type="disclaimer",
        action="shown",
        reason="channel_disclaimer_requested",
        details={"channel": normalized_channel},
    )
    return {
        "channel": normalized_channel,
        "disclaimer": PROTOTYPE_DISCLAIMER,
    }


@router.get("/audit/events")
def get_policy_audit_events(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, object]:
    events = policy_audit_log.list_events(limit=limit)
    return {
        "count": len(events),
        "events": events,
    }


@router.get("/audit/integrity")
def get_policy_audit_integrity() -> dict[str, object]:
    return policy_audit_log.verify_integrity()


@router.get("/audit/patients/{patient_id}")
def get_policy_audit_patient_timeline(
    patient_id: str,
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, object]:
    normalized_patient_id = patient_id.strip()
    if not normalized_patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")

    return policy_audit_log.get_patient_timeline(patient_id=normalized_patient_id, limit=limit)
