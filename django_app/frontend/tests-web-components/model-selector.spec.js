import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`Individual message feedback can be entered`, async ({ page }) => {
  await signIn(page);

  const currentUrl = await page.url();
  await page.goto(`${currentUrl}?test=true`);
  
  const select = await page.locator(".rb-model-selector__select");

  // The component is rendered and displaying the currently selected model
  await expect(select).toContainText("gpt-4o");

  // A new value can be selected
  await select.click();
  await page.locator("#model-option-2").click();
  await expect(select).toContainText("Claude");
 
});
