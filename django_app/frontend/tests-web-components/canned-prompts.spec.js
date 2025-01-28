import { test, expect } from "@playwright/test";
const { signIn } = require("./utils.js");

test(`Clicking canned prompts updates the text input`, async ({ page }) => {
  await signIn(page);

  const textInput = page.locator(".rb-chat-input textarea");
  await expect(textInput).toHaveValue("");

  await page.locator(".chat-options__option").nth(0).click();
  await expect(textInput).toHaveValue("Summarise this document");

  await page.locator(".chat-options__option").nth(1).click();
  await expect(textInput).toHaveValue("Draft an email about ");

  await page.locator(".chat-options__option").nth(2).click();
  await expect(textInput).toHaveValue(
    "Reformat this to assist with neurodivergent communication "
  );
});
