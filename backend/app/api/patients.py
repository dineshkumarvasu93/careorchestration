from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query

from ..data.store import patient_store
from ..policy import PROTOTYPE_DISCLAIMER

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("")
def search_patients(query: str = Query(default="", min_length=0, max_length=120)) -> dict[str, object]:
    results = patient_store.search(query)
    return {
        "query": query,
        "count": len(results),
        "results": results,
        "disclaimer": PROTOTYPE_DISCLAIMER,
    }


@router.get("/{patient_id}/profile")
def get_patient_profile(patient_id: str) -> dict[str, object]:
    profile = patient_store.get_profile(patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"patient '{patient_id}' not found")

    return {
        "profile": profile,
        "disclaimer": PROTOTYPE_DISCLAIMER,
    }


@router.post("/ingest")
def ingest_patients(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    mode = str(payload.get("mode", "reject")).strip().lower() or "reject"
    actor = str(payload.get("actor", "system")).strip() or "system"
    records = payload.get("records", [])

    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="'records' must be a list")

    result = patient_store.ingest_records(records=records, mode=mode, actor=actor)
    return {
        "policy": "synthetic-only",
        "disclaimer": PROTOTYPE_DISCLAIMER,
        **result,
    }
