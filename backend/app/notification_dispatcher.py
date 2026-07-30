from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationPolicy:
    max_retries: int
    backoff_ms: int


class NotificationDispatcher:
    """Dispatches owner and patient notifications with deterministic retry logging."""

    def default_policy(self) -> NotificationPolicy:
        max_retries = self._to_int(os.getenv("NOTIFICATION_MAX_RETRIES", "2"), default=2)
        backoff_ms = self._to_int(os.getenv("NOTIFICATION_BACKOFF_MS", "200"), default=200)
        return NotificationPolicy(max_retries=max(0, max_retries), backoff_ms=max(0, backoff_ms))

    def merge_policy(self, overrides: dict[str, object] | None) -> NotificationPolicy:
        base = self.default_policy()
        if not overrides:
            return base

        max_retries = self._to_int(overrides.get("max_retries", base.max_retries), base.max_retries)
        backoff_ms = self._to_int(overrides.get("backoff_ms", base.backoff_ms), base.backoff_ms)
        return NotificationPolicy(max_retries=max(0, max_retries), backoff_ms=max(0, backoff_ms))

    def dispatch(
        self,
        run_id: str,
        patient_id: str,
        tasks: list[dict[str, str]],
        policy: NotificationPolicy,
        simulation: dict[str, object] | None = None,
    ) -> dict[str, object]:
        recipients: list[dict[str, str]] = []
        seen_owner_keys: set[str] = set()

        for task in tasks:
            owner = str(task.get("owner", "care-coordinator"))
            owner_key = f"owner:{owner}"
            if owner_key not in seen_owner_keys:
                recipients.append({"recipient_key": owner_key, "recipient_type": "owner", "recipient_id": owner})
                seen_owner_keys.add(owner_key)

        recipients.append(
            {
                "recipient_key": f"patient:{patient_id}",
                "recipient_type": "patient",
                "recipient_id": patient_id,
            }
        )

        logs: list[dict[str, object]] = []
        success_count = 0
        failure_count = 0

        for recipient in recipients:
            recipient_key = recipient["recipient_key"]
            max_attempts = 1 + policy.max_retries
            attempt_logs: list[dict[str, object]] = []
            delivered = False

            for attempt in range(1, max_attempts + 1):
                should_fail = self._should_fail(
                    recipient_key=recipient_key,
                    attempt=attempt,
                    simulation=simulation,
                )
                if should_fail:
                    attempt_logs.append(
                        {
                            "attempt": attempt,
                            "status": "failed",
                            "backoff_ms": policy.backoff_ms * attempt,
                        }
                    )
                    continue

                delivered = True
                attempt_logs.append(
                    {
                        "attempt": attempt,
                        "status": "sent",
                        "backoff_ms": 0,
                    }
                )
                break

            if delivered:
                final_status = "sent"
                success_count += 1
            else:
                final_status = "failed"
                failure_count += 1

            logs.append(
                {
                    "run_id": run_id,
                    "recipient_key": recipient_key,
                    "recipient_type": recipient["recipient_type"],
                    "recipient_id": recipient["recipient_id"],
                    "attempts": attempt_logs,
                    "final_status": final_status,
                }
            )

        return {
            "policy": {
                "max_retries": policy.max_retries,
                "backoff_ms": policy.backoff_ms,
            },
            "count": len(logs),
            "success_count": success_count,
            "failure_count": failure_count,
            "logs": logs,
        }

    def _should_fail(
        self,
        recipient_key: str,
        attempt: int,
        simulation: dict[str, object] | None,
    ) -> bool:
        if not simulation:
            return False

        fail_first_attempts = simulation.get("fail_first_attempts", {})
        if not isinstance(fail_first_attempts, dict):
            return False

        threshold_raw = fail_first_attempts.get(recipient_key)
        if threshold_raw is None:
            return False

        threshold = self._to_int(threshold_raw, default=0)
        return attempt <= max(0, threshold)

    def _to_int(self, value: object, default: int) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default


notification_dispatcher = NotificationDispatcher()
