import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("landing page renders the heading and synthetic-data banner", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Clerkstone", level: 1 })).toBeVisible();
  await expect(page.getByText(/synthetic data — not for clinical use/i).first()).toBeVisible();
});

test("landing page has no serious or critical axe violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
  expect(serious).toEqual([]);
});
