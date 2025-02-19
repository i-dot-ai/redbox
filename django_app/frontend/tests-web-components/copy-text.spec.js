const { test, expect, sendMessage, signIn } = require("./utils.js");


test(`Content can be copied to clipboard`, async ({ page }) => {
  await signIn(page);

  await sendMessage(page);

  await page.getByText("Copy").click();
  const response = page.locator(".iai-chat-bubble__text").nth(1);

  const messageInput = page.locator(".rb-chat-input textarea");
  await messageInput.focus();
  await page.keyboard.press("Meta+V");
  expect(await response.textContent()).toEqual(await messageInput.inputValue());
});
