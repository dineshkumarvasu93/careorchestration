import { expect, test } from "@playwright/test";

test("US-018 dashboard labels and values are consistent", async ({ page }) => {
  await page.route("**/api/v1/orchestration/analytics", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        approval: {
          total_runs: 10,
          decided_runs: 8,
          approved_runs: 6,
          rejected_runs: 2,
          approval_rate_pct: 75,
        },
        conversion: {
          approved_runs: 6,
          tasks_generated_runs: 5,
          conversion_rate_pct: 83.33,
        },
        latency: {
          decision_latency_count: 8,
          average_decision_latency_seconds: 12.4,
          task_generation_latency_count: 5,
          average_task_generation_latency_seconds: 21.3,
          end_to_end_latency_count: 5,
          average_end_to_end_latency_seconds: 36.8,
        },
        widgets: [
          { key: "approval_rate", label: "Approval Rate", value: "75.00%" },
          { key: "conversion_rate", label: "Conversion Rate", value: "83.33%" },
          { key: "avg_decision_latency", label: "Avg Decision Latency (s)", value: "12.40" },
          { key: "avg_end_to_end_latency", label: "Avg End-to-End Latency (s)", value: "36.80" },
        ],
      }),
    });
  });

    await page.goto("/analytics-dashboard.html");
  await page.getByRole("button", { name: "Refresh Metrics" }).click();

  await expect(page.getByText("Approval Rate")).toBeVisible();
  await expect(page.getByText("75.00%")).toBeVisible();
  await expect(page.getByText("Conversion Rate")).toBeVisible();
  await expect(page.getByText("83.33%")).toBeVisible();

  await expect(page.getByText("Total Runs")).toBeVisible();
  await expect(page.locator("#total-runs")).toHaveText("10");
  await expect(page.locator("#approved-runs")).toHaveText("6");
  await expect(page.locator("#tasks-generated-runs")).toHaveText("5");
});
