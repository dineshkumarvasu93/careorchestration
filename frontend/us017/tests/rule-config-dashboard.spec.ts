import { expect, test } from "@playwright/test";

test("US-017 rule config dashboard publishes, activates, and lists versions", async ({ page }) => {
  await page.route("**/api/v1/orchestration/rules/versions", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        active_version: "RULES-002",
        count: 2,
        versions: [
          {
            version: "RULES-002",
            description: "Candidate rules",
            egfr_decline_threshold: 12,
          },
          {
            version: "RULES-001",
            description: "Baseline deterministic CKD rules",
            egfr_decline_threshold: 8,
          },
        ],
      }),
    });
  });

  await page.route("**/api/v1/orchestration/rules/publish", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ published: { version: "RULES-002" } }),
    });
  });

  await page.route("**/api/v1/orchestration/rules/activate", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ active_version: "RULES-002", rules: { version: "RULES-002" } }),
    });
  });

    await page.goto("/rule-config-dashboard.html");

  await page.getByLabel("Version").first().fill("RULES-002");
  await page.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Published RULES-002.")).toBeVisible();

  await page.getByLabel("Version").nth(1).fill("RULES-002");
  await page.getByRole("button", { name: "Activate" }).click();

  await expect(page.getByTestId("active-version")).toHaveText("RULES-002");
  await expect(page.getByTestId("version-list")).toContainText("RULES-002");
});
