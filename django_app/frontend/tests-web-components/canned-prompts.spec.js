import { test, expect } from "@playwright/test";
const { signIn } = require("./utils.js");

test(`Clicking canned prompts updates the text input`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  const textInput = page.locator(".iai-chat-input__input");
  await expect(textInput).toHaveValue("");

  await page.locator(".chat-options__option").nth(0).click();
  await expect(textInput).toHaveValue("Draft an agenda for a team meeting");

  await page.locator(".chat-options__option").nth(1).click();
  await expect(textInput).toHaveValue("Help me set my work objectives");

  await page.locator(".chat-options__option").nth(2).click();
  await expect(textInput).toHaveValue(
    "Describe the role of a Permanent Secretary"
  );
});
