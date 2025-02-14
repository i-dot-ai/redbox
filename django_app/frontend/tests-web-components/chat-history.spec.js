const { test, expect, sendMessage, signIn } = require("./utils.js");


test(`Chat history functionality works as expected`, async ({ page }) => {
  await signIn(page);

  const count1 = await page.evaluate(
    () => document.querySelectorAll(".rb-chat-history__link").length
  );

  // wait for chat-history to be ready
  await expect(page.locator("chat-history")).toBeVisible();

  // create a new chat
  await sendMessage(page, "Test chat");
  await expect(page.locator(".chat-title__heading")).toContainText("Test chat");

  // The chat history item has been created
  let chatHistoryItem = page.locator(".rb-chat-history__link").first();
  const count2 = await page.evaluate(
    () => document.querySelectorAll(".rb-chat-history__link").length
  );
  await expect(chatHistoryItem).toContainText("Test chat");
  expect(count2).toEqual(count1 + 1);

  // A "Today" heading has been created
  await expect(
    page.locator(".rb-chat-history__date_group").first()
  ).toContainText("Today");

  // A chat can be renamed
  await page.locator(".rb-chat-history__actions-button").first().click();
  await page.locator('button[data-action="rename"]').first().click();
  const textInput = page.locator(".rb-chat-history__text-input input").first();
  await textInput.fill("Renamed chat");
  await textInput.press("Enter");
  await expect(chatHistoryItem).toContainText("Renamed chat");

  // A chat is renamed on the server
  await page.reload();
  chatHistoryItem = page.locator(".rb-chat-history__link").first();
  await expect(chatHistoryItem).toContainText("Renamed chat");

  // A chat can be deleted
  await page.locator(".rb-chat-history__actions-button").first().click();
  await page.locator('button[data-action="delete"]').first().click();
  await page.locator('button[data-action="delete-confirm"]').first().click();
  await page.waitForTimeout(1000);
  const count3 = await page.evaluate(
    () => document.querySelectorAll(".rb-chat-history__link").length
  );
  expect(count3).toEqual(count1);

  // A chat is deleted on the server (therefore won't appear on page reload)
  await page.reload();
  const count4 = await page.evaluate(
    () => document.querySelectorAll(".rb-chat-history__link").length
  );
  expect(count4).toEqual(count3);
});
