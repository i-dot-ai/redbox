import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`A loading message is shown when streaming`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  // Loading message is visible immediately after sending a message
  await sendMessage(page);
  await expect(page.locator("loading-message")).toBeVisible();

  // And then hidden once the streaming has completed
  await expect(page.locator("loading-message")).not.toBeVisible();

});
