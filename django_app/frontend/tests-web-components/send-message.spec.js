import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`Streaming can be started and stopped`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  let sendButton = page.getByRole("button", { name: "Send" });
  let stopButton = page.getByRole("button", { name: "Stop" });

  // The Send button is visible and the Stop button isn't visible at the start
  await expect(stopButton).toBeHidden();
  await expect(sendButton).toBeVisible();

  // And that switches around once streaming occurs
  await sendMessage(page);
  await expect(stopButton).toBeVisible();
  await expect(sendButton).toBeHidden();

  // Clicking the stop button stops the streaming
  await stopButton.click();
  await expect(sendButton).toBeVisible();
  await expect(stopButton).toBeHidden();
  await expect(
    page.locator('chat-message[data-status="stopped"]')
  ).toBeVisible();
});
