import { test, expect } from "@playwright/test";
const { signIn, uploadDocument, sendMessage } = require("./utils.js");


test(`A document can be uploaded and removed before sending`, async ({ page }) => {
  await signIn(page);

  await expect(page.locator("file-status")).toHaveCount(0);
  await uploadDocument(page);
  await expect(page.locator("file-status")).toHaveText("Uploading test-upload.html");
  await expect(page.locator("file-status")).toHaveText("Complete test-upload.html");
  await expect(page.locator("file-status")).toHaveCount(1);

  await page.locator('button[aria-label="Remove test-upload.html"]').click();
  await expect(page.locator("file-status")).toHaveCount(0);

});


test(`A document can be sent`, async ({ page }) => {
  await signIn(page);

  await expect(page.locator("file-status")).toHaveCount(0);
  await uploadDocument(page);
  await expect(page.locator("file-status")).toHaveCount(1);

  await sendMessage(page);
  await expect(page.locator(".rb-uploaded-docs__item")).toContainText("test-upload.html");
  await expect(page.locator("file-status")).toHaveCount(0);

});