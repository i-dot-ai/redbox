import { test, expect } from "@playwright/test";
const { signIn } = require("./utils.js");

test(`Message input functionality`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  const messageInput = page.locator(".iai-chat-input__input");

  const height1 = await page.evaluate(
    () => document.querySelector(".iai-chat-input__input").scrollHeight
  );

  // Pressing shift + enter doesn't send the message
  await messageInput.pressSequentially("Test line 1");
  await messageInput.press("Shift+Enter");
  await messageInput.pressSequentially("Test line 2");

  // The height of the textarea increases to fit content
  const height2 = await page.evaluate(
    () => document.querySelector(".iai-chat-input__input").scrollHeight
  );
  expect(height2 > height1).toBeTruthy();

  // Check the public methods work okay
  const text1 = await page.evaluate(() =>
    document.querySelector("message-input").getValue()
  );
  expect(text1).toEqual("Test line 1\nTest line 2");
  await page.evaluate(() => document.querySelector("message-input").reset());
  expect(await messageInput.inputValue()).toEqual("");

  // Pressing enter key (without shift) sends the message
  // And the message input is cleared
  await messageInput.pressSequentially("Test line 1");
  await messageInput.press("Enter");
  expect(await messageInput.inputValue()).toEqual("");

  // And the height of the textarea returns to it's original height
  const height3 = await page.evaluate(
    () => document.querySelector(".iai-chat-input__input").scrollHeight
  );
  expect(height3).toEqual(height1);
});
