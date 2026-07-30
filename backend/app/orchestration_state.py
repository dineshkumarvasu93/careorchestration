from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .analysis_engine import analysis_engine
from .notification_dispatcher import notification_dispatcher
from .policy import policy_audit_log
from .rule_engine import rule_evaluation_engine
from .task_mapper import gap_task_mapper
from .taxonomy_registry import TaxonomyError, taxonomy_registry


class OrchestrationError(ValueError):
    """Raised for invalid orchestration operations."""


@dataclass(frozen=True)
class DecisionRecord:
    decision: str
    actor: str
    rationale: str
    timestamp_utc: str


class OrchestrationRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, object]] = {}
        self._analysis_by_id: dict[str, dict[str, object]] = {}
        self._validation_by_analysis_id: dict[str, dict[str, object]] = {}
        self._conversation_sessions: dict[str, dict[str, object]] = {}

    def create_run(self, patient_id: str, recommendations: list[dict[str, object]]) -> dict[str, object]:
        run_id = f"RUN-{uuid4()}"
        now_utc = datetime.now(timezone.utc).isoformat()
        run = {
            "run_id": run_id,
            "patient_id": patient_id,
            "status": "awaiting_approval",
            "created_at_utc": now_utc,
            "decision": "pending",
            "decision_record": None,
            "recommendations": recommendations,
            "terminated": False,
            "downstream_tasks": [],
            "timeline": [],
            "analysis_result": None,
            "validation_result": None,
            "requires_validation": False,
            "notification_dispatch": None,
        }
        self._append_timeline_event(
            run=run,
            event_type="run_created",
            actor="system",
            details={"patient_id": patient_id},
        )
        self._runs[run_id] = run
        return self._clone_run(run)

    def get_run(self, run_id: str) -> dict[str, object] | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        return self._clone_run(run)

    def get_or_create_conversation_session(self, session_id: str) -> dict[str, object]:
        normalized = session_id.strip()
        if not normalized:
            raise OrchestrationError("session_id is required")

        existing = self._conversation_sessions.get(normalized)
        if existing:
            return dict(existing)

        snapshot = {
            "session_id": normalized,
            "patient_id": None,
            "analysis_id": None,
            "run_id": None,
            "decision": None,
            "last_action": "start",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        self._conversation_sessions[normalized] = snapshot
        return dict(snapshot)

    def update_conversation_session(self, session_id: str, updates: dict[str, object]) -> dict[str, object]:
        snapshot = self.get_or_create_conversation_session(session_id)
        for key, value in updates.items():
            snapshot[key] = value

        snapshot["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        self._conversation_sessions[session_id] = snapshot
        return dict(snapshot)

    def get_conversation_session(self, session_id: str) -> dict[str, object] | None:
        snapshot = self._conversation_sessions.get(session_id)
        if not snapshot:
            return None

        return dict(snapshot)

    def trigger_analysis(self, patient_id: str, profile: dict[str, object]) -> dict[str, object]:
        result = analysis_engine.analyze(patient_id=patient_id, profile=profile)
        try:
            taxonomy_validation = taxonomy_registry.validate_gaps(
                gaps=result.get("gaps", []),
                taxonomy_version=str(result.get("taxonomy_version", "")).strip() or None,
            )
        except TaxonomyError as exc:
            raise OrchestrationError(f"analysis payload rejected: {exc}") from exc

        result["taxonomy_validation"] = taxonomy_validation
        recommendations = [
            {
                "gap_id": str(gap.get("gap_id", "GAP-UNKNOWN")),
                "recommendation_id": str(gap.get("recommendation_id", "REC-UNKNOWN")),
                "title": str(gap.get("title", "Recommendation")),
            }
            for gap in result.get("gaps", [])
            if isinstance(gap, dict)
        ]

        run = self.create_run(patient_id=patient_id, recommendations=recommendations)
        persisted_run = self._runs[run["run_id"]]
        persisted_run["analysis_result"] = result
        persisted_run["taxonomy_version"] = result.get("taxonomy_version")
        persisted_run["status"] = "analysis_completed"
        persisted_run["requires_validation"] = True
        self._append_timeline_event(
            run=persisted_run,
            event_type="analysis_completed",
            actor="system",
            details={"analysis_id": result["analysis_id"], "risk": result["risk"]},
        )

        persisted = dict(result)
        persisted["run_id"] = run["run_id"]
        self._analysis_by_id[result["analysis_id"]] = persisted

        policy_audit_log.record(
            event_type="analysis",
            action="completed",
            reason="explicit_trigger",
            details={
                "analysis_id": result["analysis_id"],
                "patient_id": patient_id,
                "run_id": run["run_id"],
                "actor": "system",
                "channel": "api",
            },
        )

        return persisted

    def get_analysis_result(self, analysis_id: str) -> dict[str, object] | None:
        result = self._analysis_by_id.get(analysis_id)
        if not result:
            return None

        return dict(result)

    def validate_analysis(
        self,
        analysis_id: str,
        confidence_threshold: float,
        actor: str,
    ) -> dict[str, object]:
        analysis = self._analysis_by_id.get(analysis_id)
        if not analysis:
            raise OrchestrationError("analysis not found")

        run_id = str(analysis.get("run_id", ""))
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        validation = rule_evaluation_engine.evaluate(
            analysis=analysis,
            confidence_threshold=confidence_threshold,
        )
        validation["analysis_id"] = analysis_id
        validation["run_id"] = run_id
        validation["actor"] = actor

        run["validation_result"] = validation
        analysis["validation"] = validation
        self._validation_by_analysis_id[analysis_id] = dict(validation)

        actionable_recommendations: list[dict[str, str]] = []
        decisions = validation.get("decisions", [])
        if isinstance(decisions, list):
            for decision in decisions:
                if not isinstance(decision, dict):
                    continue
                if decision.get("auto_action_allowed") is True:
                    recommendation_id = str(decision.get("recommendation_id", "REC-UNKNOWN"))
                    gap_id = str(decision.get("gap_id", "GAP-UNKNOWN"))
                    title = recommendation_id
                    for recommendation in run["recommendations"]:
                        if recommendation.get("recommendation_id") == recommendation_id:
                            title = str(recommendation.get("title", recommendation_id))
                            break
                    actionable_recommendations.append(
                        {
                            "gap_id": gap_id,
                            "recommendation_id": recommendation_id,
                            "title": title,
                        }
                    )

        run["recommendations"] = actionable_recommendations
        overall_status = str(validation.get("overall_status", "valid"))
        run["status"] = "review_required" if overall_status in {"flagged", "needs_review"} else "validated"

        self._append_timeline_event(
            run=run,
            event_type="rules_validated",
            actor=actor,
            details={
                "analysis_id": analysis_id,
                "overall_status": overall_status,
                "actionable_recommendation_count": len(actionable_recommendations),
            },
        )

        policy_audit_log.record(
            event_type="analysis_validation",
            action="evaluated",
            reason="rule_engine_execution",
            details={
                "analysis_id": analysis_id,
                "run_id": run_id,
                "patient_id": str(run.get("patient_id", "")),
                "overall_status": overall_status,
                "actor": actor,
                "channel": "api",
            },
        )

        return dict(validation)

    def get_validation_result(self, analysis_id: str) -> dict[str, object] | None:
        validation = self._validation_by_analysis_id.get(analysis_id)
        if not validation:
            return None

        return dict(validation)

    def list_analysis_results(self, patient_id: str | None = None) -> list[dict[str, object]]:
        results = [dict(item) for item in self._analysis_by_id.values()]
        if patient_id:
            normalized = patient_id.strip()
            results = [item for item in results if str(item.get("patient_id", "")) == normalized]

        results.sort(key=lambda item: str(item.get("triggered_at_utc", "")), reverse=True)
        return results

    def record_decision(self, run_id: str, decision: str, actor: str, rationale: str) -> dict[str, object]:
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        normalized_decision = decision.strip().lower()
        if normalized_decision not in {"approve", "reject"}:
            raise OrchestrationError("decision must be 'approve' or 'reject'")

        if run["decision"] != "pending":
            raise OrchestrationError("decision already recorded for this run")

        now_utc = datetime.now(timezone.utc).isoformat()
        decision_record = DecisionRecord(
            decision=normalized_decision,
            actor=actor,
            rationale=rationale,
            timestamp_utc=now_utc,
        )
        run["decision"] = normalized_decision
        run["decision_record"] = {
            "decision": decision_record.decision,
            "actor": decision_record.actor,
            "rationale": decision_record.rationale,
            "timestamp_utc": decision_record.timestamp_utc,
        }
        self._append_timeline_event(
            run=run,
            event_type="decision_recorded",
            actor=actor,
            details={
                "outcome": normalized_decision,
                "rationale": rationale,
                "timestamp_utc": decision_record.timestamp_utc,
            },
        )

        if normalized_decision == "approve":
            run["status"] = "approved"
            policy_audit_log.record(
                event_type="orchestration_gate",
                action="approved",
                reason="coordinator_decision",
                details={
                    "run_id": run_id,
                    "patient_id": str(run.get("patient_id", "")),
                    "actor": actor,
                    "channel": "api",
                },
            )
        else:
            run["status"] = "rejected"
            run["terminated"] = True
            policy_audit_log.record(
                event_type="orchestration_gate",
                action="rejected",
                reason="coordinator_decision",
                details={
                    "run_id": run_id,
                    "patient_id": str(run.get("patient_id", "")),
                    "actor": actor,
                    "channel": "api",
                    "rationale": rationale,
                },
            )

        return self._clone_run(run)

    def generate_downstream_tasks(
        self,
        run_id: str,
        notification_options: dict[str, object] | None = None,
    ) -> dict[str, object]:
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        if run["decision"] == "pending":
            raise OrchestrationError("approval required before downstream task generation")

        if run["decision"] == "reject":
            raise OrchestrationError("orchestration terminated after rejection; no task creation allowed")

        if run.get("requires_validation") is True:
            validation_result = run.get("validation_result")
            if not isinstance(validation_result, dict):
                raise OrchestrationError("rule validation required before downstream task generation")

            overall_status = str(validation_result.get("overall_status", "valid"))
            if overall_status in {"flagged", "needs_review"}:
                raise OrchestrationError(
                    "run is in explicit human review state; auto-action task generation blocked"
                )

        existing_tasks = run["downstream_tasks"]
        if existing_tasks:
            return {
                "run_id": run_id,
                "created_count": 0,
                "tasks": existing_tasks,
                "status": "already_generated",
            }

        recommendations = run["recommendations"]
        mapped_recommendations, missing_mappings = gap_task_mapper.map_recommendations(recommendations)
        if missing_mappings:
            run["status"] = "mapping_blocked"
            self._append_timeline_event(
                run=run,
                event_type="task_mapping_failed",
                actor="system",
                details={"missing_mappings": missing_mappings},
            )
            policy_audit_log.record(
                event_type="task_mapping",
                action="failed",
                reason="missing_template_mapping",
                details={
                    "run_id": run_id,
                    "patient_id": str(run.get("patient_id", "")),
                    "missing_mappings": missing_mappings,
                    "actor": "system",
                    "channel": "api",
                },
            )
            missing_ids = ", ".join(
                sorted({item["recommendation_id"] for item in missing_mappings})
            )
            raise OrchestrationError(
                f"missing task mappings for recommendations: {missing_ids}"
            )

        generated_tasks: list[dict[str, str]] = []
        now_utc = datetime.now(timezone.utc)
        for index, mapping in enumerate(mapped_recommendations, start=1):
            recommendation_id = str(mapping.get("recommendation_id", f"REC-{index:03d}"))
            gap_id = str(mapping.get("gap_id", "GAP-UNKNOWN"))
            created_at_utc = now_utc.isoformat()
            due_at_utc = (now_utc + timedelta(days=2)).isoformat()
            generated_tasks.append(
                {
                    "task_id": f"TASK-{index:03d}",
                    "run_id": run_id,
                    "recommendation_id": recommendation_id,
                    "originating_gap_id": gap_id,
                    "template_id": str(mapping.get("template_id", "TPL-UNKNOWN")),
                    "task_title": str(mapping.get("task_title", "Mapped Task")),
                    "owner": str(mapping.get("owner", "care-coordinator")),
                    "status": "created",
                    "created_at_utc": created_at_utc,
                    "updated_at_utc": created_at_utc,
                    "due_at_utc": due_at_utc,
                    "escalated": False,
                    "escalation_events": [],
                    "history": [
                        {
                            "from_status": "none",
                            "to_status": "created",
                            "changed_at_utc": created_at_utc,
                            "actor": "system",
                            "reason": "task_generated",
                        }
                    ],
                }
            )

        run["downstream_tasks"] = generated_tasks
        run["status"] = "tasks_generated"
        self._append_timeline_event(
            run=run,
            event_type="tasks_generated",
            actor="system",
            details={"task_count": len(generated_tasks)},
        )

        policy_audit_log.record(
            event_type="orchestration_gate",
            action="tasks_generated",
            reason="approved_run",
            details={
                "run_id": run_id,
                "patient_id": str(run.get("patient_id", "")),
                "task_count": len(generated_tasks),
                "actor": "system",
                "channel": "api",
            },
        )

        notification_policy = notification_dispatcher.merge_policy(
            (notification_options or {}).get("policy")
            if isinstance(notification_options, dict)
            else None
        )
        simulation = (
            (notification_options or {}).get("simulation")
            if isinstance(notification_options, dict)
            else None
        )
        notification_report = notification_dispatcher.dispatch(
            run_id=run_id,
            patient_id=str(run.get("patient_id", "unknown")),
            tasks=generated_tasks,
            policy=notification_policy,
            simulation=simulation if isinstance(simulation, dict) else None,
        )
        run["notification_dispatch"] = notification_report

        self._append_timeline_event(
            run=run,
            event_type="notifications_dispatched",
            actor="system",
            details={
                "success_count": notification_report["success_count"],
                "failure_count": notification_report["failure_count"],
                "max_retries": notification_report["policy"]["max_retries"],
                "backoff_ms": notification_report["policy"]["backoff_ms"],
            },
        )

        policy_audit_log.record(
            event_type="notification_dispatch",
            action="completed" if notification_report["failure_count"] == 0 else "partial_failure",
            reason="task_creation_notification",
            details={
                "run_id": run_id,
                "patient_id": str(run.get("patient_id", "")),
                "success_count": notification_report["success_count"],
                "failure_count": notification_report["failure_count"],
                "actor": "system",
                "channel": "api",
            },
        )

        return {
            "run_id": run_id,
            "created_count": len(generated_tasks),
            "tasks": generated_tasks,
            "status": "generated",
            "notifications": notification_report,
        }

    def list_tasks(self, run_id: str) -> list[dict[str, str]]:
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        return list(run["downstream_tasks"])

    def update_task_status(
        self,
        run_id: str,
        task_id: str,
        next_status: str,
        actor: str,
        reason: str,
    ) -> dict[str, object]:
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        task = self._find_task(run, task_id)
        if not task:
            raise OrchestrationError("task not found")

        normalized_next_status = next_status.strip().lower()
        allowed_statuses = {"created", "in_progress", "completed", "cancelled"}
        if normalized_next_status not in allowed_statuses:
            raise OrchestrationError("invalid task status transition target")

        current_status = str(task.get("status", "created"))
        transition_map = {
            "created": {"in_progress", "cancelled"},
            "in_progress": {"completed", "cancelled"},
            "completed": set(),
            "cancelled": set(),
        }
        if normalized_next_status not in transition_map.get(current_status, set()):
            raise OrchestrationError(
                f"invalid transition from '{current_status}' to '{normalized_next_status}'"
            )

        changed_at_utc = datetime.now(timezone.utc).isoformat()
        history = task.get("history", [])
        if not isinstance(history, list):
            history = []
        history.append(
            {
                "from_status": current_status,
                "to_status": normalized_next_status,
                "changed_at_utc": changed_at_utc,
                "actor": actor,
                "reason": reason,
            }
        )

        task["status"] = normalized_next_status
        task["updated_at_utc"] = changed_at_utc
        task["history"] = history

        self._append_timeline_event(
            run=run,
            event_type="task_status_changed",
            actor=actor,
            details={
                "task_id": task_id,
                "from_status": current_status,
                "to_status": normalized_next_status,
            },
        )
        policy_audit_log.record(
            event_type="task_lifecycle",
            action="status_changed",
            reason="manual_transition",
            details={
                "run_id": run_id,
                "patient_id": str(run.get("patient_id", "")),
                "task_id": task_id,
                "from_status": current_status,
                "to_status": normalized_next_status,
                "actor": actor,
                "channel": "api",
            },
        )

        return dict(task)

    def check_overdue_tasks(
        self,
        run_id: str,
        actor: str,
        current_time_utc: str | None = None,
    ) -> dict[str, object]:
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        if current_time_utc:
            try:
                parsed = datetime.fromisoformat(current_time_utc)
            except ValueError as exc:
                raise OrchestrationError("invalid current_time_utc value") from exc

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            now_utc = parsed
        else:
            now_utc = datetime.now(timezone.utc)
        escalated: list[dict[str, str]] = []

        for task in run["downstream_tasks"]:
            status = str(task.get("status", "created"))
            if status in {"completed", "cancelled"}:
                continue

            due_at_text = str(task.get("due_at_utc", "")).strip()
            if not due_at_text:
                continue

            try:
                due_at = datetime.fromisoformat(due_at_text)
                if due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            if due_at >= now_utc:
                continue

            if bool(task.get("escalated", False)):
                continue

            escalated_at = now_utc.isoformat()
            escalation_events = task.get("escalation_events", [])
            if not isinstance(escalation_events, list):
                escalation_events = []

            escalation_events.append(
                {
                    "escalated_at_utc": escalated_at,
                    "actor": actor,
                    "reason": "task_overdue",
                }
            )
            task["escalation_events"] = escalation_events
            task["escalated"] = True
            task["updated_at_utc"] = escalated_at

            self._append_timeline_event(
                run=run,
                event_type="task_escalated",
                actor=actor,
                details={
                    "task_id": str(task.get("task_id", "unknown")),
                    "due_at_utc": due_at_text,
                },
            )
            policy_audit_log.record(
                event_type="task_lifecycle",
                action="escalated",
                reason="task_overdue",
                details={
                    "run_id": run_id,
                    "patient_id": str(run.get("patient_id", "")),
                    "task_id": str(task.get("task_id", "unknown")),
                    "actor": actor,
                    "channel": "api",
                },
            )

            escalated.append(
                {
                    "task_id": str(task.get("task_id", "unknown")),
                    "status": str(task.get("status", "unknown")),
                    "due_at_utc": due_at_text,
                }
            )

        return {
            "run_id": run_id,
            "checked_at_utc": now_utc.isoformat(),
            "escalated_count": len(escalated),
            "escalated_tasks": escalated,
        }

    def get_tracking_view(self, run_id: str) -> dict[str, object]:
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        tasks = run["downstream_tasks"]
        status_counts: dict[str, int] = {}
        escalation_count = 0

        task_cards: list[dict[str, object]] = []
        for task in tasks:
            status = str(task.get("status", "unknown"))
            status_counts[status] = status_counts.get(status, 0) + 1
            escalated = bool(task.get("escalated", False))
            if escalated:
                escalation_count += 1

            task_cards.append(
                {
                    "task_id": str(task.get("task_id", "")),
                    "task_title": str(task.get("task_title", "")),
                    "owner": str(task.get("owner", "")),
                    "status": status,
                    "originating_gap_id": str(task.get("originating_gap_id", "")),
                    "due_at_utc": str(task.get("due_at_utc", "")),
                    "updated_at_utc": str(task.get("updated_at_utc", "")),
                    "escalated": escalated,
                    "escalation_events": list(task.get("escalation_events", [])),
                }
            )

        return {
            "run_id": run_id,
            "patient_id": str(run.get("patient_id", "unknown")),
            "run_status": str(run.get("status", "unknown")),
            "task_count": len(task_cards),
            "status_counts": status_counts,
            "escalation_count": escalation_count,
            "tasks": task_cards,
        }

    def get_analytics_summary(self) -> dict[str, object]:
        runs = list(self._runs.values())
        total_runs = len(runs)
        approved_runs = 0
        rejected_runs = 0
        tasks_generated_runs = 0

        decision_latencies: list[float] = []
        task_generation_latencies: list[float] = []
        end_to_end_latencies: list[float] = []

        for run in runs:
            decision = str(run.get("decision", "pending"))
            if decision == "approve":
                approved_runs += 1
            elif decision == "reject":
                rejected_runs += 1

            has_tasks_generated = any(
                isinstance(event, dict) and str(event.get("event_type", "")) == "tasks_generated"
                for event in run.get("timeline", [])
            )
            if has_tasks_generated:
                tasks_generated_runs += 1

            created_at = self._parse_utc(str(run.get("created_at_utc", "")))
            decision_record = run.get("decision_record")
            decision_at = None
            if isinstance(decision_record, dict):
                decision_at = self._parse_utc(str(decision_record.get("timestamp_utc", "")))

            tasks_generated_at = self._find_timeline_event_timestamp(run=run, event_type="tasks_generated")

            if created_at and decision_at:
                decision_latencies.append(max(0.0, (decision_at - created_at).total_seconds()))

            if decision_at and tasks_generated_at:
                task_generation_latencies.append(
                    max(0.0, (tasks_generated_at - decision_at).total_seconds())
                )

            if created_at and tasks_generated_at:
                end_to_end_latencies.append(max(0.0, (tasks_generated_at - created_at).total_seconds()))

        decided_runs = approved_runs + rejected_runs
        approval_rate = round((approved_runs / decided_runs) * 100, 2) if decided_runs else 0.0
        conversion_rate = round((tasks_generated_runs / approved_runs) * 100, 2) if approved_runs else 0.0

        average_decision_latency = (
            round(sum(decision_latencies) / len(decision_latencies), 2)
            if decision_latencies
            else 0.0
        )
        average_task_generation_latency = (
            round(sum(task_generation_latencies) / len(task_generation_latencies), 2)
            if task_generation_latencies
            else 0.0
        )
        average_end_to_end_latency = (
            round(sum(end_to_end_latencies) / len(end_to_end_latencies), 2)
            if end_to_end_latencies
            else 0.0
        )

        return {
            "approval": {
                "total_runs": total_runs,
                "decided_runs": decided_runs,
                "approved_runs": approved_runs,
                "rejected_runs": rejected_runs,
                "approval_rate_pct": approval_rate,
            },
            "conversion": {
                "approved_runs": approved_runs,
                "tasks_generated_runs": tasks_generated_runs,
                "conversion_rate_pct": conversion_rate,
            },
            "latency": {
                "decision_latency_count": len(decision_latencies),
                "average_decision_latency_seconds": average_decision_latency,
                "task_generation_latency_count": len(task_generation_latencies),
                "average_task_generation_latency_seconds": average_task_generation_latency,
                "end_to_end_latency_count": len(end_to_end_latencies),
                "average_end_to_end_latency_seconds": average_end_to_end_latency,
            },
            "widgets": [
                {
                    "key": "approval_rate",
                    "label": "Approval Rate",
                    "value": f"{approval_rate:.2f}%",
                },
                {
                    "key": "conversion_rate",
                    "label": "Conversion Rate",
                    "value": f"{conversion_rate:.2f}%",
                },
                {
                    "key": "avg_decision_latency",
                    "label": "Avg Decision Latency (s)",
                    "value": f"{average_decision_latency:.2f}",
                },
                {
                    "key": "avg_end_to_end_latency",
                    "label": "Avg End-to-End Latency (s)",
                    "value": f"{average_end_to_end_latency:.2f}",
                },
            ],
        }

    def _find_timeline_event_timestamp(self, run: dict[str, object], event_type: str) -> datetime | None:
        for event in run.get("timeline", []):
            if not isinstance(event, dict):
                continue
            if str(event.get("event_type", "")) != event_type:
                continue
            parsed = self._parse_utc(str(event.get("timestamp_utc", "")))
            if parsed:
                return parsed

        return None

    def _parse_utc(self, timestamp: str) -> datetime | None:
        text = timestamp.strip()
        if not text:
            return None

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _find_task(self, run: dict[str, object], task_id: str) -> dict[str, object] | None:
        for task in run["downstream_tasks"]:
            if str(task.get("task_id", "")) == task_id:
                return task

        return None

    def get_timeline(self, run_id: str) -> list[dict[str, object]]:
        run = self._runs.get(run_id)
        if not run:
            raise OrchestrationError("run not found")

        return [dict(event) for event in run["timeline"]]

    def _append_timeline_event(
        self,
        run: dict[str, object],
        event_type: str,
        actor: str,
        details: dict[str, object],
    ) -> None:
        run["timeline"].append(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "actor": actor,
                "details": details,
            }
        )

    def _clone_run(self, run: dict[str, object]) -> dict[str, object]:
        cloned = dict(run)
        cloned["recommendations"] = list(run["recommendations"])
        cloned["downstream_tasks"] = list(run["downstream_tasks"])
        cloned["timeline"] = [dict(event) for event in run["timeline"]]
        cloned["analysis_result"] = dict(run["analysis_result"]) if run["analysis_result"] else None
        cloned["validation_result"] = dict(run["validation_result"]) if run["validation_result"] else None
        cloned["requires_validation"] = bool(run.get("requires_validation", False))
        cloned["notification_dispatch"] = (
            dict(run["notification_dispatch"]) if run.get("notification_dispatch") else None
        )
        return cloned


orchestration_run_store = OrchestrationRunStore()
