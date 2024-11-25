import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`Chat title functionality works as expected`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  // There is a hidden chat title for new chats
  const chatTitle = page.locator(".chat-title__heading");
  await expect(chatTitle).toContainText("Current chat");
  await expect(chatTitle).toHaveClass(/govuk-visually-hidden/);

  // A title appears when a message is sent
  await sendMessage(page);
  await expect(chatTitle).toContainText("Testing");
  await expect(chatTitle).not.toHaveClass(/govuk-visually-hidden/);

  // The title can be edited
  await page.locator(".chat-title__edit-btn").click();
  let textInput = page.locator(".chat-title__input");
  await expect(textInput).toBeFocused();
  await textInput.fill("Updated chat title");
  await textInput.press("Enter");
  await expect(chatTitle).toContainText("Updated chat title");
});
