import { test, expect } from "@playwright/test";
const { signIn, uploadDocument } = require("./utils.js");

test(`Documents get added to the chats page selector once processing is complete`, async ({ page }) => {
  
  await signIn(page);
  await uploadDocument(page);

  await page.goto("/chats");

  const docCount = await page.locator("document-selector input").count();  
  await expect(page.locator("document-selector input").nth(docCount - 1)).not.toBeVisible();
  
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      document.body.addEventListener("doc-complete", () => {
        resolve();
      });
    });
  });
  
  await expect(page.locator("document-selector input").nth(docCount - 1)).toBeVisible();

});
