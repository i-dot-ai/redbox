const { test, expect } = require("./utils.js");


test(`The Department Selector works as expected`, async ({ page }) => {
  
  await page.goto("/sign-up-page-1");

  expect(await page.locator("#id_business_unit")).not.toBeVisible();

  await page.locator("#department").selectOption({ label: "Cabinet Office" });
  expect(await page.locator("#id_business_unit")).toBeVisible();

  await page.locator("#id_business_unit").selectOption({ label: "Central Costs" });
});
