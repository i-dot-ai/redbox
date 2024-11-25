import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`A message is shown when a document is uploading`, async ({ page }) => {
  await signIn(page);

  await page.goto("/upload");

  // Prevent the form from submitting so we can test the loading message without actually uploading a file
  await page.evaluate(() => {
    document.querySelector('form').addEventListener('submit', (evt) => {
      evt.preventDefault();
    });
  });

  await page.locator('button[type="submit"]').click();
  await expect(page.getByText("Uploading")).toBeVisible();
  
});
