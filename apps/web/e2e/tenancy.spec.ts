import { expect, test } from "@playwright/test";

/** UI-level tenancy checks. Server-side isolation is proven by the API suite
 * (apps/api/tests/test_security_cross_tenant.py); these confirm the interface
 * reflects the caller's actual membership and permissions. */

test("administration shows the organisation profile", async ({ page }) => {
  await page.goto("/administration");

  await expect(page.getByRole("heading", { name: "Administration" })).toBeVisible();
  await expect(page.getByLabel("Trading name")).toHaveValue("Southern Cross Logistics");
});

test("applicability tab exposes jurisdictions and CoR roles", async ({ page }) => {
  await page.goto("/administration");
  await page.getByRole("button", { name: "Applicability" }).click();

  await expect(page.getByText("New South Wales")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Chain of Responsibility roles" }),
  ).toBeVisible();
  await expect(page.getByText("Loading manager")).toBeVisible();
});

test("non-HVNL jurisdictions are marked so rule packs are not assumed", async ({
  page,
}) => {
  await page.goto("/administration");
  await page.getByRole("button", { name: "Applicability" }).click();

  // WA and NT run their own heavy vehicle legislation.
  const badges = page.getByText("non-HVNL");
  await expect(badges).toHaveCount(2);
});

test("accreditation is presented as voluntary, never as a requirement", async ({
  page,
}) => {
  await page.goto("/administration");
  await page.getByRole("button", { name: "Applicability" }).click();

  const accreditation = page.locator("section", { hasText: "Accreditation" }).last();
  await expect(accreditation.getByText(/voluntary/)).toBeVisible();
  await expect(accreditation.getByText(/not required in order to operate/)).toBeVisible();

  // Nothing may frame accreditation as an obligation or a deficiency. Phrased
  // as specific bad copy rather than a broad keyword match, so the correct
  // wording ("not required in order to operate") does not trip it.
  const prohibited = [
    /accreditation (is )?required/i,
    /missing accreditation/i,
    /non-compliant/i,
    /must be accredited/i,
    /accreditation gap/i,
  ];
  const body = await accreditation.innerText();
  for (const pattern of prohibited) {
    expect(body, `accreditation copy must not match ${pattern}`).not.toMatch(pattern);
  }
});

test("members tab lists people in this organisation only", async ({ page }) => {
  await page.goto("/administration");
  await page.getByRole("button", { name: "Members" }).click();

  await expect(page.getByText("sam.chen@southerncross.example")).toBeVisible();
  // A member of the other seeded organisation must never appear here.
  await expect(page.getByText("jo.alvarez@outbackfreight.example")).toHaveCount(0);
});

test("operations tab lists this organisation's records", async ({ page }) => {
  await page.goto("/administration");
  await page.getByRole("button", { name: "Operations" }).click();

  await expect(page.getByText("Southern Cross Logistics Depot")).toBeVisible();
  await expect(page.getByText("Primary Fleet")).toBeVisible();
});
