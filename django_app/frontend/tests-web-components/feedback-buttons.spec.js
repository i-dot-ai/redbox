import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`Individual message feedback can be entered`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  // The component is visible after sending a message
  await sendMessage(page);
  await expect(page.locator("feedback-buttons")).toBeVisible();

  // The component can be interacted with
  await page.locator('[data-rating="3"]').click();
  await expect(page.getByText("Thanks for the feedback")).toBeVisible();

});
