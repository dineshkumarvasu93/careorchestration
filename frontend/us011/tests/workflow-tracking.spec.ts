import { expect, test } from "@playwright/test";

test("US-011 tracking view shows task statuses and escalation markers", async ({ page }) => {
  await page.route("**/api/v1/orchestration/runs/RUN-DEMO-001/tracking", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "RUN-DEMO-001",
        patient_id: "PT-0001",
        run_status: "tasks_generated",
        task_count: 2,
        escalation_count: 1,
        tasks: [
          {
            task_id: "TASK-001",
            task_title: "Order UACR Lab",
            owner: "lab-coordinator",
            status: "in_progress",
            originating_gap_id: "GAP-UACR-MISSING",
            due_at_utc: "2026-07-25T10:00:00+00:00",
            escalated: true,
            escalation_events: [{ escalated_at_utc: "2026-07-27T10:00:00+00:00" }],
          },
          {
            task_id: "TASK-002",
            task_title: "Schedule Nephrology Follow-up",
            owner: "nephrology-coordinator",
            status: "created",
            originating_gap_id: "GAP-EGFR-DECLINE",
            due_at_utc: "2026-08-01T10:00:00+00:00",
            escalated: false,
            escalation_events: [],
          },
        ],
      }),
    });
  });

    await page.goto("/workflow-tracking.html");
  await page.getByLabel("Run ID").fill("RUN-DEMO-001");
  await page.getByRole("button", { name: "Load Tracking" }).click();

  await expect(page.getByTestId("tracking-table")).toBeVisible();
  await expect(page.getByTestId("escalation-count")).toHaveText("1");
  await expect(page.getByText("in_progress")).toBeVisible();
  await expect(page.getByText("Escalated")).toBeVisible();
});
