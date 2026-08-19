import { expect, test } from "@playwright/test";

const NAV_ROUTES: Array<{ label: string; path: string; heading: string }> = [
  { label: "Assurance Overview", path: "/overview", heading: "Assurance Overview" },
  { label: "Controls", path: "/controls", heading: "Controls" },
  { label: "Evidence", path: "/evidence", heading: "Evidence" },
  { label: "Findings", path: "/findings", heading: "Findings" },
  { label: "Corrective Actions", path: "/corrective-actions", heading: "Corrective Actions" },
  { label: "Audit Readiness", path: "/audit-readiness", heading: "Audit Readiness" },
  { label: "Compliance Assistant", path: "/compliance-assistant", heading: "Compliance Assistant" },
  { label: "Administration", path: "/administration", heading: "Administration" },
];

test("root path redirects to the Assurance Overview dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/overview$/);
  await expect(page.getByRole("heading", { name: "Assurance Overview" })).toBeVisible();
});

test("dashboard loads with live data from the API", async ({ page }) => {
  await page.goto("/overview");

  await expect(page.getByText("High-risk findings", { exact: true })).toBeVisible();
  await expect(page.getByText("Fatigue / Work-Rest")).toBeVisible();
  // Confirms the page rendered real API data, not the loading/error state.
  // (Next.js renders its own hidden role="alert" route announcer, so assert
  // on our visible error banner copy rather than the ARIA role alone.)
  await expect(page.getByText("Couldn't load this data")).toHaveCount(0);
});

test("left navigation lists all 8 sections and each one loads", async ({ page }) => {
  await page.goto("/overview");

  const nav = page.getByRole("navigation", { name: "Primary" });
  for (const item of NAV_ROUTES) {
    await expect(nav.getByRole("link", { name: item.label })).toBeVisible();
  }

  for (const item of NAV_ROUTES) {
    await nav.getByRole("link", { name: item.label }).click();
    await expect(page).toHaveURL(new RegExp(`${item.path}$`));
    await expect(page.getByRole("heading", { name: item.heading })).toBeVisible();
  }
});

test("organisation selector switches the active organisation", async ({ page }) => {
  await page.goto("/overview");

  const select = page.getByLabel("Organisation");
  await expect(select).toBeVisible();

  const options = await select.locator("option").allTextContents();
  expect(options.length).toBeGreaterThan(1);

  await select.selectOption({ label: options[1] });
  await expect(select).toHaveValue(await select.locator("option").nth(1).getAttribute("value") ?? "");
});

test("user profile menu opens and shows account details", async ({ page }) => {
  await page.goto("/overview");

  await page.getByRole("button", { name: /Sam Chen/i }).click();
  await expect(page.getByRole("menuitem", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Compliance Manager")).toBeVisible();
});

test("page is usable at a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/overview");

  // Sidebar is off-canvas on mobile; the menu toggle opens it.
  const nav = page.getByRole("navigation", { name: "Primary" });
  await expect(nav).not.toBeInViewport();

  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(nav.getByRole("link", { name: "Findings" })).toBeVisible();
});
