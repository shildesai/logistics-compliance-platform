import { expect, test } from "@playwright/test";

/** Control Explorer: the Regulation → Obligation → Risk → Control → Evidence
 * → Tests chain, and the guarantee that regulatory logic stays server-side. */

test.beforeEach(async ({ page }) => {
  await page.goto("/controls");
  await page.getByRole("button", { name: /CTL-FAT-001/ }).click();
  await expect(page.getByText("Why this control exists")).toBeVisible();
});

/** The control summary card. The page wraps the detail panel in its own
 * <section>, so take the innermost match rather than the wrapper. */
const summaryCard = (page: import("@playwright/test").Page) =>
  page.locator("section").filter({ hasText: "PSOE relevance" }).last();

test("shows the control with its in-force version", async ({ page }) => {
  const summary = summaryCard(page);

  await expect(
    page.getByRole("heading", { name: "Fatigue monitoring and intervention" }),
  ).toBeVisible();
  await expect(summary.getByText("v2", { exact: true })).toBeVisible();
  // DOM text is lower-case; the capitalised appearance comes from CSS.
  await expect(summary.getByText("compliance manager", { exact: true })).toBeVisible();
  await expect(summary.getByText("continuous", { exact: true })).toBeVisible();
});

test("renders the full chain from regulation down to the control", async ({ page }) => {
  const chain = page.locator("section", { hasText: "Why this control exists" });

  await expect(chain.getByText("Heavy Vehicle National Law").first()).toBeVisible();
  await expect(chain.getByText("Manage heavy vehicle driver fatigue")).toBeVisible();
  await expect(chain.getByText("Driver operates beyond work/rest limits")).toBeVisible();
  await expect(chain.getByText("CTL-FAT-001").first()).toBeVisible();
});

test("a shared control shows every obligation it satisfies", async ({ page }) => {
  const chain = page.locator("section", { hasText: "Why this control exists" });

  await expect(chain.getByText(/2 obligations are satisfied/)).toBeVisible();
  await expect(chain.getByText("Manage heavy vehicle driver fatigue")).toBeVisible();
  await expect(
    chain.getByText("Do not create unreasonable transport safety risk through scheduling"),
  ).toBeVisible();
  await expect(chain.getByText("primary mitigation")).toBeVisible();
});

test("shows tests, evidence requirements and remediation", async ({ page }) => {
  const tests = page.locator("section", { hasText: "Tests and evidence" });

  await expect(tests.getByText("Work-time threshold exception")).toBeVisible();
  await expect(tests.getByText("Electronic work diary records")).toBeVisible();
  await expect(tests.getByText("Investigate work-time exceedance")).toBeVisible();
});

test("distinguishes the test types and flags human review", async ({ page }) => {
  const tests = page.locator("section", { hasText: "Tests and evidence" });

  await expect(tests.getByText("deterministic")).toBeVisible();
  await expect(tests.getByText("analytical")).toBeVisible();
  await expect(tests.getByText("manual", { exact: true })).toBeVisible();
  // Every seeded test requires human confirmation before it becomes material.
  await expect(tests.getByText("human review").first()).toBeVisible();
});

test("rule configuration is displayed as inert data, not interpreted", async ({ page }) => {
  const tests = page.locator("section", { hasText: "Tests and evidence" });

  // Raw keys and values are shown verbatim for review. The UI must never
  // compute against these — evaluation is server-side only.
  await expect(tests.getByText("threshold_exceeded")).toBeVisible();
  await expect(tests.getByText("limit_minutes")).toBeVisible();
  await expect(tests.getByText("720")).toBeVisible();
});

test("shows version history including superseded versions", async ({ page }) => {
  const history = page.locator("section").filter({ hasText: "Version history" }).last();

  await expect(history.getByText("superseded", { exact: true })).toBeVisible();
  await expect(history.getByText("active", { exact: true })).toBeVisible();
  await expect(history.getByText(/Moved from daily review to continuous/)).toBeVisible();
});

test("as-at date resolves to the version that applied then", async ({ page }) => {
  // Before the 2026-02-01 amendment the control was daily and semi-automated.
  await page.getByLabel("View the graph as at").fill("2025-06-01");

  const summary = summaryCard(page);
  await expect(summary.getByText("daily", { exact: true })).toBeVisible({
    timeout: 10_000,
  });
  await expect(summary.getByText("semi automated", { exact: true })).toBeVisible();
});

test("as-at before the graph existed reports no version in force", async ({ page }) => {
  await page.getByLabel("View the graph as at").fill("2020-01-01");

  await expect(
    page.getByText("No version in force on this date").first(),
  ).toBeVisible({ timeout: 10_000 });
});
