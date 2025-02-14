const { test, expect } = require("./utils.js");


test(`The animated logo can be paused`, async ({ page }) => {

  await page.goto("/");

  await expect(page.locator(".rb-icon")).toHaveClass("rb-icon rb-icon--animated");
  
  await page.keyboard.press("Escape");
  await expect(page.locator(".rb-icon")).toHaveClass("rb-icon");

});


test.describe('Non-JS tests', () => {

  test.use({ javaScriptEnabled: false });
  test(`The logo doesn't animate if JavaScript isn't running`, async ({ page }) => {

    await page.goto("/");

    await expect(page.locator(".rb-icon")).toHaveClass("rb-icon");

  });

});
