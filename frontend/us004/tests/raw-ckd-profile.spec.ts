import { test, expect } from "@playwright/test";

// This test validates that the recommendation panel remains in
// "Not analyzed yet" state before any analysis trigger is invoked.
test("US-004: raw profile view does not show AI output before analysis", async ({ page }) => {
  await page.route("**/api/v1/patients?query=John", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        query: "John",
        count: 1,
        results: [{ patient_id: "PT-0001", name: "John Smith", ckd_stage: "Stage 3" }],
      }),
    });
  });

  await page.route("**/api/v1/patients/PT-0001/profile", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        profile: {
          patient_id: "PT-0001",
          demographics: { first_name: "John", last_name: "Smith", age: 58, gender: "Male" },
          ckd_stage: "Stage 3",
          egfr: { current: 48, previous: 58, unit: "mL/min/1.73m2", trend: "declining" },
          uacr: { status: "missing", last_value: null, last_test_date: null },
          medication_summary: ["Lisinopril 10 mg daily"],
          last_nephrology_visit_date: "2025-03-15",
        },
      }),
    });
  });

    await page.goto("/raw-ckd-profile.html");
  await expect(page.getByTestId("prototype-disclaimer")).toBeVisible();
  await expect(page.getByTestId("prototype-disclaimer")).toContainText("Prototype only");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("button", { name: /John Smith/ }).click();

  await expect(page.getByTestId("raw-ckd-values")).toBeVisible();
  await expect(page.getByTestId("recommendation-state")).toHaveText("Not analyzed yet");
  await expect(page.getByRole("button", { name: "Analyze Patient" })).toBeDisabled();
});
