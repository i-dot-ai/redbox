import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`The activity log can be expanded when there is more than one item`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  await sendMessage(page);

  // The first button is hidden, as there's only 1 user item
  await expect(page.locator("activity-button button").first()).toBeHidden();

  // The first AI log item is hidden, as there's more than 1 AI item
  await expect(page.locator(".rb-activity__item--ai").first()).toBeHidden();

  // Clicking the expand button shows all AI items
  await page.locator("activity-button button").nth(1).click();
  await expect(page.locator(".rb-activity__item--ai").first()).toBeVisible();

});
