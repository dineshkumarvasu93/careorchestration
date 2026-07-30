from __future__ import annotations

from datetime import datetime, timezone

from .rule_config_store import rule_config_store


class RuleEvaluationEngine:
    """Deterministic prototype rule engine for recommendation validation."""

    def evaluate(self, analysis: dict[str, object], confidence_threshold: float = 0.8) -> dict[str, object]:
        active_rules = rule_config_store.get_active_rules()
        known_gap_ids = {str(item) for item in active_rules.get("known_gap_ids", [])}
        gaps = analysis.get("gaps", [])
        if not isinstance(gaps, list):
            gaps = []

        decisions: list[dict[str, object]] = []
        has_flagged = False
        has_needs_review = False

        for gap in gaps:
            if not isinstance(gap, dict):
                continue

            gap_id = str(gap.get("gap_id", ""))
            recommendation_id = str(gap.get("recommendation_id", "REC-UNKNOWN"))
            confidence = float(gap.get("confidence", 0.0))

            if gap_id not in known_gap_ids:
                classification = "flagged"
                auto_action_allowed = False
                reason = "unknown_gap_vocabulary"
                has_flagged = True
            elif confidence < confidence_threshold:
                classification = "needs_review"
                auto_action_allowed = False
                reason = "low_confidence"
                has_needs_review = True
            else:
                classification = "valid"
                auto_action_allowed = True
                reason = "rule_compliant"

            decisions.append(
                {
                    "gap_id": gap_id,
                    "recommendation_id": recommendation_id,
                    "classification": classification,
                    "auto_action_allowed": auto_action_allowed,
                    "confidence": confidence,
                    "reason": reason,
                }
            )

        if has_flagged:
            overall_status = "flagged"
        elif has_needs_review:
            overall_status = "needs_review"
        else:
            overall_status = "valid"

        return {
            "overall_status": overall_status,
            "confidence_threshold": confidence_threshold,
            "rule_version": str(active_rules.get("version", "unknown")),
            "decisions": decisions,
            "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
            "traceability": "TR-004",
        }


rule_evaluation_engine = RuleEvaluationEngine()
