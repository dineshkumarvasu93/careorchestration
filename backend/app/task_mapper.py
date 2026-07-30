from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskTemplate:
    template_id: str
    owner: str
    task_title: str


class GapTaskMapper:
    """Deterministic mapping from care-gap recommendations to task templates."""

    def __init__(self) -> None:
        self._templates_by_recommendation: dict[str, TaskTemplate] = {
            "REC-UACR-001": TaskTemplate(
                template_id="TPL-LAB-UACR",
                owner="lab-coordinator",
                task_title="Order UACR Lab",
            ),
            "REC-NEPH-002": TaskTemplate(
                template_id="TPL-NEPH-FOLLOWUP",
                owner="nephrology-coordinator",
                task_title="Schedule Nephrology Follow-up",
            ),
            "REC-MONITOR-003": TaskTemplate(
                template_id="TPL-ROUTINE-MONITOR",
                owner="care-coordinator",
                task_title="Continue Routine Monitoring",
            ),
            # Backward-compatible templates used in manual run tests.
            "REC-001": TaskTemplate(
                template_id="TPL-LAB-UACR",
                owner="lab-coordinator",
                task_title="Order UACR Lab",
            ),
            "REC-002": TaskTemplate(
                template_id="TPL-NEPH-FOLLOWUP",
                owner="nephrology-coordinator",
                task_title="Schedule Nephrology Follow-up",
            ),
        }

    def map_recommendations(
        self,
        recommendations: list[dict[str, object]],
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        mapped: list[dict[str, str]] = []
        missing: list[dict[str, str]] = []

        for recommendation in recommendations:
            recommendation_id = str(recommendation.get("recommendation_id", "REC-UNKNOWN"))
            gap_id = str(recommendation.get("gap_id", "GAP-UNKNOWN"))
            template = self._templates_by_recommendation.get(recommendation_id)

            if not template:
                missing.append(
                    {
                        "recommendation_id": recommendation_id,
                        "gap_id": gap_id,
                    }
                )
                continue

            mapped.append(
                {
                    "recommendation_id": recommendation_id,
                    "gap_id": gap_id,
                    "template_id": template.template_id,
                    "owner": template.owner,
                    "task_title": template.task_title,
                }
            )

        return mapped, missing


gap_task_mapper = GapTaskMapper()
