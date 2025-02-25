const { test, expect, signIn } = require("./utils.js");


test(`A different model can be selected`, async ({ page }) => {
  await signIn(page);
  
  const select = await page.locator(".rb-model-selector__select");

  // The component is rendered and displaying the currently selected model
  await expect(select).toContainText("gpt-4o");

  // max-tokens is set correctly
  expect(await page.locator("#max-tokens").inputValue()).toBe("128000");

  // A new value can be selected
  await select.click();
  await page.locator("#model-option-0").click();
  await page.waitForTimeout(100);
  await expect(select).toContainText("Claude");

  // max-tokens has updated
  expect(await page.locator("#max-tokens").inputValue()).not.toBe("128000");

  // The new value is also set as the active option (this is different to the selected option)
  await select.click();
  await expect(page.locator(".rb-model-selector__option--active")).toContainText("Claude");
 
});
