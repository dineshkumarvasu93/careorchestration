from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query, Request
from uuid import uuid4

from ..orchestration_state import OrchestrationError, orchestration_run_store
from ..data.store import patient_store
from ..policy import PROTOTYPE_DISCLAIMER, policy_audit_log
from ..rule_config_store import RuleConfigError, rule_config_store
from ..taxonomy_registry import TaxonomyError, taxonomy_registry

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


def _resolve_role(payload: dict[str, object] | None, actor: str, default_role: str) -> str:
    explicit = ""
    if isinstance(payload, dict):
        explicit = str(payload.get("role", "")).strip().lower()
    if explicit:
        return explicit

    normalized_actor = actor.strip().lower()
    if "admin" in normalized_actor:
        return "admin"
    if "scheduler" in normalized_actor:
        return "scheduler"
    if "viewer" in normalized_actor:
        return "viewer"
    if "auditor" in normalized_actor:
        return "auditor"
    if "coordinator" in normalized_actor:
        return "coordinator"

    return default_role


def _require_authorized_role(
    *,
    role: str,
    allowed_roles: set[str],
    actor: str,
    action: str,
    channel: str,
    run_id: str | None = None,
    patient_id: str | None = None,
) -> None:
    if role in allowed_roles:
        return

    policy_audit_log.record(
        event_type="authorization",
        action="denied",
        reason="insufficient_role",
        details={
            "channel": channel,
            "actor": actor,
            "role": role,
            "requested_action": action,
            "allowed_roles": sorted(allowed_roles),
            "run_id": run_id,
            "patient_id": patient_id,
        },
    )
    raise HTTPException(status_code=403, detail=f"forbidden: role '{role}' cannot perform '{action}'")


def _resolve_cx_session_id(payload: dict[str, object]) -> str:
    session_info = payload.get("sessionInfo", {}) if isinstance(payload, dict) else {}
    if isinstance(session_info, dict):
        session_path = str(session_info.get("session", "")).strip()
        if session_path:
            return session_path

    explicit = str(payload.get("session_id", "")).strip() if isinstance(payload, dict) else ""
    return explicit or f"cx-session-{uuid4()}"


def _resolve_cx_action(payload: dict[str, object]) -> str:
    explicit = str(payload.get("action", "")).strip().lower() if isinstance(payload, dict) else ""
    if explicit:
        return explicit

    fulfillment_info = payload.get("fulfillmentInfo", {}) if isinstance(payload, dict) else {}
    tag = str(fulfillment_info.get("tag", "")).strip().lower() if isinstance(fulfillment_info, dict) else ""
    return tag


def _resolve_cx_parameters(payload: dict[str, object]) -> dict[str, object]:
    explicit = payload.get("parameters", {}) if isinstance(payload, dict) else {}
    if isinstance(explicit, dict) and explicit:
        return explicit

    session_info = payload.get("sessionInfo", {}) if isinstance(payload, dict) else {}
    session_params = session_info.get("parameters", {}) if isinstance(session_info, dict) else {}
    return session_params if isinstance(session_params, dict) else {}


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "message": "orchestration router is reachable"}


@router.get("/routes")
def list_orchestration_routes(request: Request) -> dict[str, list[dict[str, object]]]:
    routes = []
    for route in request.app.routes:
        path = getattr(route, "path", "")
        methods = sorted(getattr(route, "methods", []))
        if path.startswith("/api/v1/orchestration"):
            routes.append({"path": path, "methods": methods})

    return {"routes": routes}


@router.get("/rules/versions")
def list_rule_versions() -> dict[str, object]:
    versions = rule_config_store.list_versions()
    active = rule_config_store.get_active_rules()
    return {
        "active_version": active["version"],
        "count": len(versions),
        "versions": versions,
    }


@router.get("/rules/active")
def get_active_rule_version() -> dict[str, object]:
    rules = rule_config_store.get_active_rules()
    return {
        "active_version": rules["version"],
        "rules": rules,
    }


@router.get("/taxonomy/versions")
def list_taxonomy_versions() -> dict[str, object]:
    versions = taxonomy_registry.list_versions()
    active = taxonomy_registry.get_active()
    return {
        "active_version": active["version"],
        "count": len(versions),
        "versions": versions,
    }


@router.get("/taxonomy/active")
def get_active_taxonomy_version() -> dict[str, object]:
    taxonomy = taxonomy_registry.get_active()
    return {
        "active_version": taxonomy["version"],
        "taxonomy": taxonomy,
    }


@router.post("/taxonomy/publish")
def publish_taxonomy_version(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    actor = str(payload.get("actor", "coordinator")).strip() or "coordinator"
    role = _resolve_role(payload, actor=actor, default_role="coordinator")
    _require_authorized_role(
        role=role,
        allowed_roles={"coordinator", "admin"},
        actor=actor,
        action="taxonomy_publish",
        channel="api",
    )

    try:
        published = taxonomy_registry.publish(payload)
    except TaxonomyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    policy_audit_log.record(
        event_type="taxonomy",
        action="published",
        reason="taxonomy_created",
        details={
            "channel": "api",
            "actor": actor,
            "role": role,
            "taxonomy_version": published["version"],
        },
    )

    return {"published": published}


@router.post("/taxonomy/activate")
def activate_taxonomy_version(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    version = str(payload.get("version", "")).strip()
    actor = str(payload.get("actor", "coordinator")).strip() or "coordinator"
    role = _resolve_role(payload, actor=actor, default_role="coordinator")
    _require_authorized_role(
        role=role,
        allowed_roles={"coordinator", "admin"},
        actor=actor,
        action="taxonomy_activate",
        channel="api",
    )

    try:
        result = taxonomy_registry.activate(version)
    except TaxonomyError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc

    policy_audit_log.record(
        event_type="taxonomy",
        action="activated",
        reason="taxonomy_selected",
        details={
            "channel": "api",
            "actor": actor,
            "role": role,
            "taxonomy_version": result["active_version"],
        },
    )

    return result


@router.post("/taxonomy/validate")
def validate_taxonomy_payload(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    taxonomy_version = str(payload.get("taxonomy_version", "")).strip() or None
    gaps = payload.get("gaps", [])
    try:
        validation = taxonomy_registry.validate_gaps(gaps=gaps, taxonomy_version=taxonomy_version)
    except TaxonomyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "valid",
        **validation,
    }


@router.post("/taxonomy/compatibility/check")
def check_taxonomy_compatibility(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    source_version = str(payload.get("source_version", "")).strip()
    target_version = str(payload.get("target_version", "")).strip()
    gaps = payload.get("gaps", [])

    if not source_version:
        raise HTTPException(status_code=400, detail="source_version is required")
    if not target_version:
        raise HTTPException(status_code=400, detail="target_version is required")

    try:
        result = taxonomy_registry.check_compatibility(
            source_version=source_version,
            target_version=target_version,
            gaps=gaps,
        )
    except TaxonomyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result


@router.post("/rules/publish")
def publish_rule_version(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    actor = str(payload.get("actor", "coordinator")).strip() or "coordinator"
    role = _resolve_role(payload, actor=actor, default_role="coordinator")
    _require_authorized_role(
        role=role,
        allowed_roles={"coordinator", "admin"},
        actor=actor,
        action="rules_publish",
        channel="api",
    )

    try:
        published = rule_config_store.publish(payload)
    except RuleConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    policy_audit_log.record(
        event_type="rule_config",
        action="published",
        reason="ruleset_created",
        details={
            "channel": "api",
            "actor": actor,
            "role": role,
            "rule_version": published["version"],
        },
    )

    return {
        "published": published,
    }


@router.post("/rules/activate")
def activate_rule_version(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    version = str(payload.get("version", "")).strip()
    actor = str(payload.get("actor", "coordinator")).strip() or "coordinator"
    role = _resolve_role(payload, actor=actor, default_role="coordinator")
    _require_authorized_role(
        role=role,
        allowed_roles={"coordinator", "admin"},
        actor=actor,
        action="rules_activate",
        channel="api",
    )

    try:
        result = rule_config_store.activate(version)
    except RuleConfigError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc

    policy_audit_log.record(
        event_type="rule_config",
        action="activated",
        reason="ruleset_selected",
        details={
            "channel": "api",
            "actor": actor,
            "role": role,
            "rule_version": result["active_version"],
        },
    )

    return result


@router.get("/conversation/start")
def start_conversation_session(
    coordinator_id: str = Query(default="coordinator", min_length=1, max_length=64),
) -> dict[str, str]:
    policy_audit_log.record(
        event_type="disclaimer",
        action="shown",
        reason="conversation_session_start",
        details={"channel": "conversation", "coordinator_id": coordinator_id},
    )
    return {
        "channel": "conversation",
        "coordinator_id": coordinator_id,
        "message": "Conversation workflow initialized.",
        "disclaimer": PROTOTYPE_DISCLAIMER,
    }


@router.post("/cx/webhook")
def cx_webhook_fulfillment(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    session_id = _resolve_cx_session_id(payload)
    action = _resolve_cx_action(payload)
    parameters = _resolve_cx_parameters(payload)

    if not action:
        raise HTTPException(status_code=400, detail="action is required for CX webhook")

    session_context = orchestration_run_store.get_or_create_conversation_session(session_id)
    response_payload: dict[str, object] = {}
    response_text = ""

    if action == "search":
        query = str(parameters.get("query", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required for search")

        matches = patient_store.search(query)
        selected_patient_id = str(parameters.get("patient_id", "")).strip()
        if not selected_patient_id and matches:
            selected_patient_id = str(matches[0].get("patient_id", "")).strip()

        if selected_patient_id:
            session_context = orchestration_run_store.update_conversation_session(
                session_id,
                {"patient_id": selected_patient_id, "last_action": "search"},
            )

        response_payload = {
            "query": query,
            "match_count": len(matches),
            "matches": matches,
            "selected_patient_id": selected_patient_id or None,
        }
        response_text = f"Found {len(matches)} patient match(es)."

    elif action == "analyze":
        patient_id = str(parameters.get("patient_id", "")).strip() or str(
            session_context.get("patient_id", "")
        ).strip()
        if not patient_id:
            raise HTTPException(status_code=400, detail="patient_id is required for analyze")

        profile = patient_store.get_profile(patient_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"patient '{patient_id}' not found")

        analysis = orchestration_run_store.trigger_analysis(patient_id=patient_id, profile=profile)
        session_context = orchestration_run_store.update_conversation_session(
            session_id,
            {
                "patient_id": patient_id,
                "analysis_id": analysis["analysis_id"],
                "run_id": analysis["run_id"],
                "last_action": "analyze",
            },
        )

        response_payload = {
            "analysis_id": analysis["analysis_id"],
            "run_id": analysis["run_id"],
            "risk": analysis["risk"],
            "gaps": analysis["gaps"],
            "gap_count": len(analysis.get("gaps", [])),
            "confidence": analysis["confidence"],
        }
        response_text = "Analysis completed. You can now review recommendations."

    elif action == "review":
        analysis_id = str(parameters.get("analysis_id", "")).strip() or str(
            session_context.get("analysis_id", "")
        ).strip()
        if not analysis_id:
            raise HTTPException(status_code=400, detail="analysis_id is required for review")

        confidence_threshold_raw = parameters.get("confidence_threshold", 0.8)
        try:
            confidence_threshold = float(confidence_threshold_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="confidence_threshold must be numeric")

        try:
            validation = orchestration_run_store.validate_analysis(
                analysis_id=analysis_id,
                confidence_threshold=confidence_threshold,
                actor="cx-webhook",
            )
        except OrchestrationError as exc:
            detail = str(exc)
            status = 404 if "not found" in detail else 409
            raise HTTPException(status_code=status, detail=detail) from exc

        session_context = orchestration_run_store.update_conversation_session(
            session_id,
            {
                "analysis_id": analysis_id,
                "run_id": validation["run_id"],
                "last_action": "review",
            },
        )

        response_payload = {
            "analysis_id": analysis_id,
            "overall_status": validation["overall_status"],
            "decision_count": len(validation.get("decisions", [])),
            "run_id": validation["run_id"],
        }
        response_text = "Review completed. Submit approve or reject decision."

    elif action == "decision":
        run_id = str(parameters.get("run_id", "")).strip() or str(
            session_context.get("run_id", "")
        ).strip()
        decision = str(parameters.get("decision", "")).strip().lower()
        rationale = str(parameters.get("rationale", "")).strip()
        actor = str(parameters.get("actor", "cx-coordinator")).strip() or "cx-coordinator"
        role = _resolve_role(parameters if isinstance(parameters, dict) else None, actor=actor, default_role="coordinator")
        _require_authorized_role(
            role=role,
            allowed_roles={"coordinator", "admin"},
            actor=actor,
            action="decision_submit",
            channel="cx",
            run_id=run_id or None,
            patient_id=str(session_context.get("patient_id", "")).strip() or None,
        )

        if not run_id:
            raise HTTPException(status_code=400, detail="run_id is required for decision")
        if decision not in {"approve", "reject"}:
            raise HTTPException(status_code=400, detail="decision must be approve or reject")
        if decision == "reject" and not rationale:
            raise HTTPException(status_code=400, detail="rationale is required for reject decision")

        try:
            run = orchestration_run_store.record_decision(
                run_id=run_id,
                decision=decision,
                actor=actor,
                rationale=rationale,
            )
        except OrchestrationError as exc:
            detail = str(exc)
            status = 404 if "not found" in detail else 409
            raise HTTPException(status_code=status, detail=detail) from exc
        session_context = orchestration_run_store.update_conversation_session(
            session_id,
            {
                "run_id": run_id,
                "decision": decision,
                "last_action": "decision",
            },
        )

        response_payload = {
            "run_id": run_id,
            "decision": decision,
            "run_status": run["status"],
            "terminated": run["terminated"],
        }
        response_text = "Decision captured. Confirm to continue."

    elif action == "confirm":
        run_id = str(parameters.get("run_id", "")).strip() or str(
            session_context.get("run_id", "")
        ).strip()
        if not run_id:
            raise HTTPException(status_code=400, detail="run_id is required for confirm")

        run_snapshot = orchestration_run_store.get_run(run_id)
        if not run_snapshot:
            raise HTTPException(status_code=404, detail="run not found")

        if run_snapshot.get("decision") == "approve":
            try:
                generation = orchestration_run_store.generate_downstream_tasks(run_id=run_id)
            except OrchestrationError as exc:
                detail = str(exc)
                status = 404 if "not found" in detail else 409
                raise HTTPException(status_code=status, detail=detail) from exc
            response_payload = {
                "run_id": run_id,
                "confirmation": "approved",
                "task_count": generation["created_count"],
                "tasks": generation["tasks"],
            }
            response_text = "Approved path confirmed and tasks generated."
        else:
            response_payload = {
                "run_id": run_id,
                "confirmation": "rejected",
                "task_count": 0,
            }
            response_text = "Rejected path confirmed. No tasks created."

        session_context = orchestration_run_store.update_conversation_session(
            session_id,
            {"run_id": run_id, "last_action": "confirm"},
        )

    else:
        raise HTTPException(status_code=400, detail=f"unsupported CX action '{action}'")

    policy_audit_log.record(
        event_type="conversation_webhook",
        action=action,
        reason="cx_fulfillment",
        details={
            "session_id": session_id,
            "channel": "cx",
            "actor": "cx-webhook",
            "run_id": session_context.get("run_id"),
            "patient_id": session_context.get("patient_id"),
        },
    )

    session_parameters = {
        "session_id": session_id,
        "patient_id": session_context.get("patient_id"),
        "analysis_id": session_context.get("analysis_id"),
        "run_id": session_context.get("run_id"),
        "decision": session_context.get("decision"),
        "last_action": session_context.get("last_action"),
    }
    session_parameters.update(response_payload)

    return {
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [response_text],
                    }
                }
            ]
        },
        "sessionInfo": {
            "session": session_id,
            "parameters": session_parameters,
        },
        "payload": {
            "channel": "conversation",
            "disclaimer": PROTOTYPE_DISCLAIMER,
            "result": response_payload,
        },
    }


@router.post("/runs")
def create_orchestration_run(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    patient_id = str(payload.get("patient_id", "")).strip()
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")

    recommendations = payload.get("recommendations", [])
    if not isinstance(recommendations, list) or not recommendations:
        raise HTTPException(status_code=400, detail="recommendations must be a non-empty list")

    normalized_recommendations = [dict(item) for item in recommendations if isinstance(item, dict)]
    if len(normalized_recommendations) != len(recommendations):
        raise HTTPException(status_code=400, detail="every recommendation must be an object")

    run = orchestration_run_store.create_run(
        patient_id=patient_id,
        recommendations=normalized_recommendations,
    )
    return {"run": run, "disclaimer": PROTOTYPE_DISCLAIMER}


@router.post("/analysis/trigger")
def trigger_analysis(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    patient_id = str(payload.get("patient_id", "")).strip()
    if not patient_id:
        raise HTTPException(status_code=400, detail="patient_id is required")

    profile = patient_store.get_profile(patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"patient '{patient_id}' not found")

    try:
        result = orchestration_run_store.trigger_analysis(patient_id=patient_id, profile=profile)
    except OrchestrationError as exc:
        detail = str(exc)
        raise HTTPException(status_code=400, detail=detail) from exc

    return {
        "analysis": result,
        "disclaimer": PROTOTYPE_DISCLAIMER,
    }


@router.get("/analysis/{analysis_id}")
def get_analysis_result(analysis_id: str) -> dict[str, object]:
    result = orchestration_run_store.get_analysis_result(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="analysis not found")

    return {"analysis": result}


@router.post("/analysis/{analysis_id}/validate")
def validate_analysis(
    analysis_id: str,
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    confidence_threshold_raw = payload.get("confidence_threshold", 0.8)
    actor = str(payload.get("actor", "rule-engine")).strip() or "rule-engine"

    try:
        confidence_threshold = float(confidence_threshold_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="confidence_threshold must be numeric")

    if confidence_threshold <= 0 or confidence_threshold > 1:
        raise HTTPException(status_code=400, detail="confidence_threshold must be between 0 and 1")

    try:
        validation = orchestration_run_store.validate_analysis(
            analysis_id=analysis_id,
            confidence_threshold=confidence_threshold,
            actor=actor,
        )
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return {"validation": validation}


@router.get("/analysis/{analysis_id}/validation")
def get_analysis_validation_result(analysis_id: str) -> dict[str, object]:
    validation = orchestration_run_store.get_validation_result(analysis_id)
    if not validation:
        raise HTTPException(status_code=404, detail="validation not found")

    return {"validation": validation}


@router.get("/analysis")
def list_analysis_results(
    patient_id: str = Query(default="", min_length=0, max_length=64),
) -> dict[str, object]:
    normalized_patient_id = patient_id.strip() or None
    results = orchestration_run_store.list_analysis_results(patient_id=normalized_patient_id)
    return {
        "count": len(results),
        "results": results,
    }


@router.get("/runs/{run_id}")
def get_orchestration_run(run_id: str) -> dict[str, object]:
    run = orchestration_run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")

    return {"run": run}


@router.post("/runs/{run_id}/decision")
def submit_approval_decision(run_id: str, payload: dict[str, object] = Body(...)) -> dict[str, object]:
    decision = str(payload.get("decision", "")).strip().lower()
    actor = str(payload.get("actor", "coordinator")).strip() or "coordinator"
    role = _resolve_role(payload, actor=actor, default_role="coordinator")
    run_snapshot = orchestration_run_store.get_run(run_id)
    patient_id = str(run_snapshot.get("patient_id", "")).strip() if run_snapshot else None
    _require_authorized_role(
        role=role,
        allowed_roles={"coordinator", "admin"},
        actor=actor,
        action="decision_submit",
        channel="api",
        run_id=run_id,
        patient_id=patient_id or None,
    )

    rationale = str(payload.get("rationale", "")).strip()
    if decision == "reject" and not rationale:
        raise HTTPException(status_code=400, detail="rationale is required for reject decision")

    try:
        run = orchestration_run_store.record_decision(
            run_id=run_id,
            decision=decision,
            actor=actor,
            rationale=rationale,
        )
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return {"run": run}


@router.post("/runs/{run_id}/tasks/generate")
def generate_downstream_tasks(
    run_id: str,
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    actor = str(payload.get("actor", "coordinator")).strip() if isinstance(payload, dict) else "coordinator"
    if not actor:
        actor = "coordinator"
    role = _resolve_role(payload if isinstance(payload, dict) else None, actor=actor, default_role="coordinator")
    run_snapshot = orchestration_run_store.get_run(run_id)
    patient_id = str(run_snapshot.get("patient_id", "")).strip() if run_snapshot else None
    _require_authorized_role(
        role=role,
        allowed_roles={"coordinator", "admin"},
        actor=actor,
        action="tasks_generate",
        channel="api",
        run_id=run_id,
        patient_id=patient_id or None,
    )

    policy_payload = payload.get("notification_policy", {}) if isinstance(payload, dict) else {}
    simulation_payload = payload.get("notification_simulation", {}) if isinstance(payload, dict) else {}
    notification_options = {
        "policy": policy_payload if isinstance(policy_payload, dict) else {},
        "simulation": simulation_payload if isinstance(simulation_payload, dict) else {},
    }

    try:
        result = orchestration_run_store.generate_downstream_tasks(
            run_id=run_id,
            notification_options=notification_options,
        )
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return result


@router.get("/runs/{run_id}/tasks")
def list_downstream_tasks(run_id: str) -> dict[str, object]:
    try:
        tasks = orchestration_run_store.list_tasks(run_id)
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return {"run_id": run_id, "count": len(tasks), "tasks": tasks}


@router.post("/runs/{run_id}/tasks/{task_id}/status")
def update_task_status(
    run_id: str,
    task_id: str,
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    next_status = str(payload.get("status", "")).strip().lower()
    actor = str(payload.get("actor", "coordinator")).strip() or "coordinator"
    role = _resolve_role(payload, actor=actor, default_role="coordinator")
    run_snapshot = orchestration_run_store.get_run(run_id)
    patient_id = str(run_snapshot.get("patient_id", "")).strip() if run_snapshot else None
    _require_authorized_role(
        role=role,
        allowed_roles={"coordinator", "admin", "owner"},
        actor=actor,
        action="task_status_update",
        channel="api",
        run_id=run_id,
        patient_id=patient_id or None,
    )

    reason = str(payload.get("reason", "status_update")).strip() or "status_update"

    if not next_status:
        raise HTTPException(status_code=400, detail="status is required")

    try:
        task = orchestration_run_store.update_task_status(
            run_id=run_id,
            task_id=task_id,
            next_status=next_status,
            actor=actor,
            reason=reason,
        )
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return {"task": task}


@router.post("/runs/{run_id}/escalation/check")
def check_task_escalations(
    run_id: str,
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    actor = str(payload.get("actor", "scheduler")).strip() or "scheduler"
    role = _resolve_role(payload, actor=actor, default_role="scheduler")
    run_snapshot = orchestration_run_store.get_run(run_id)
    patient_id = str(run_snapshot.get("patient_id", "")).strip() if run_snapshot else None
    _require_authorized_role(
        role=role,
        allowed_roles={"scheduler", "admin"},
        actor=actor,
        action="escalation_check",
        channel="api",
        run_id=run_id,
        patient_id=patient_id or None,
    )

    current_time_utc = str(payload.get("current_time_utc", "")).strip() or None
    try:
        report = orchestration_run_store.check_overdue_tasks(
            run_id=run_id,
            actor=actor,
            current_time_utc=current_time_utc,
        )
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return report


@router.get("/runs/{run_id}/tracking")
def get_workflow_tracking(run_id: str) -> dict[str, object]:
    try:
        tracking = orchestration_run_store.get_tracking_view(run_id=run_id)
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return tracking


@router.get("/analytics")
def get_orchestration_analytics() -> dict[str, object]:
    return orchestration_run_store.get_analytics_summary()


@router.get("/runs/{run_id}/timeline")
def get_orchestration_timeline(run_id: str) -> dict[str, object]:
    try:
        events = orchestration_run_store.get_timeline(run_id)
    except OrchestrationError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail else 409
        raise HTTPException(status_code=status, detail=detail) from exc

    return {"run_id": run_id, "count": len(events), "events": events}
