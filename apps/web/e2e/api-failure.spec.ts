import { expect, test } from "@playwright/test";

/** Regression guard: when the API is unreachable the dashboard must surface an
 * error, not sit on a loading state forever. The happy-path suite cannot catch
 * this, so the API is failed deliberately here. */

test("dashboard shows an error instead of loading forever when the API is down", async ({
  page,
}) => {
  await page.route("**/api/v1/**", (route) => route.abort("connectionrefused"));

  await page.goto("/overview");

  await expect(page.getByText("Couldn't load this data.")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/Could not reach the API/)).toBeVisible();
  await expect(page.getByText("Loading…")).toHaveCount(0);
});

test("a failing dashboard endpoint surfaces an error on that page", async ({ page }) => {
  // Organisations still load, but the overview payload fails.
  await page.route("**/api/v1/dashboard/overview**", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "internal_error",
          message: "An unexpected error occurred",
          path: "/api/v1/dashboard/overview",
          timestamp: "2026-08-19T00:00:00Z",
        },
      }),
    }),
  );

  await page.goto("/overview");

  await expect(page.getByText("Couldn't load this data.")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("An unexpected error occurred")).toBeVisible();
});

test("navigation still works while the API is failing", async ({ page }) => {
  await page.route("**/api/v1/**", (route) => route.abort("connectionrefused"));

  await page.goto("/overview");
  await expect(page.getByText("Couldn't load this data.")).toBeVisible({ timeout: 10_000 });

  const nav = page.getByRole("navigation", { name: "Primary" });
  await nav.getByRole("link", { name: "Findings" }).click();

  await expect(page).toHaveURL(/\/findings$/);
  await expect(page.getByRole("heading", { name: "Findings" })).toBeVisible();
});
