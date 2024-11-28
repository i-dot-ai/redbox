import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`Individual message feedback can be entered`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  await sendMessage(page);

  // The component is visible after clicking the relevant action button
  await page.locator(".rb-action-buttons__button--rate").click();
  await expect(page.getByText("Rate this response:")).toBeVisible();

  // The component can be interacted with
  await page.locator('[data-rating="3"]').click();
  await expect(page.getByText("Thanks for the feedback")).toBeVisible();

});
