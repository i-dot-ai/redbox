const { test, signIn, expect } = require("./utils.js");

test(`The tour runs when it should do`, async ({ page }) => {
  await signIn(page);

  // the tour doesn't show normally
  await expect(page.locator(".introjs-tooltip")).toHaveCount(0);

  // the tour does show when a user clicks the tour button
  await page.getByText("Training").click();
  await page.getByText("Take the tour").click();
  await expect(page.locator(".introjs-tooltip")).toHaveCount(1);

  // the tour doesn't show again next time
  await page.reload();
  await expect(page.locator(".introjs-tooltip")).toHaveCount(0);

});
