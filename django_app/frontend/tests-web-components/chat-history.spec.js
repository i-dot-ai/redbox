import { test, expect } from "@playwright/test";
const signIn = require("./_sign-in.js");

test(`Chat history functionality works as expected`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  await page.evaluate(() => {
    document.querySelector("chat-history").addChat("session-id", "Test chat");
  });

  // The chat history item has been created
  const chatHistoryItem = page.locator(".rb-chat-history__link");
  await expect(chatHistoryItem).toContainText("Test chat");
  await expect(chatHistoryItem).toHaveAttribute("href", "/chats/session-id");

  // A "Today" heading has been created
  await expect(page.locator(".rb-chat-history__date_group")).toContainText(
    "Today"
  );

  // A chat can be renamed
  await page.locator(".rb-chat-history__actions-button").click();
  await page.locator('button[data-action="rename"]').click();
  const textInput = page.locator(".rb-chat-history__text-input input");
  await textInput.fill("Renamed chat");
  await textInput.press("Enter");
  await expect(chatHistoryItem).toContainText("Renamed chat");

  // A chat can be deleted
  await page.locator(".rb-chat-history__actions-button").click();
  await page.locator('button[data-action="delete"]').click();
  await page.locator('button[data-action="delete-confirm"]').click();
  await page.waitForTimeout(100);
  expect(await page.$(".rb-chat-history__link")).toBeFalsy();
});
