import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`A different model can be selected`, async ({ page }) => {
  await signIn(page);
  
  const select = await page.locator(".rb-model-selector__select");

  // The component is rendered and displaying the currently selected model
  await expect(select).toContainText("gpt-4o");

  // A new value can be selected
  await select.click();
  await page.locator("#model-option-2").click();
  await expect(select).toContainText("Claude");

  // The new value is also set as the active option (this is different to the selected option)
  await select.click();
  await expect(page.locator(".rb-model-selector__option--active")).toContainText("Claude");
 
});
