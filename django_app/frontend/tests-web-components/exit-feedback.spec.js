import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`Exit feedback can be entered`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  // Exit feedback isn't visible until a response has been received
  let feedbackButton = page.locator(".exit-feedback__toggle-button");
  await expect(feedbackButton).toBeHidden();

  await sendMessage(page);

  // Enter exit feedback
  await feedbackButton.click();
  await page.locator(".exit-feedback__button--yes").click();
  await page.locator(".exit-feedback__send-button").click();
  await page.waitForTimeout(100);
  await expect(page.locator(".exit-feedback__confirmation-text")).toBeVisible();
});
