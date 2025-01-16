import { test, expect } from "@playwright/test";
const { signIn, uploadDocument } = require("./utils.js");

test(`File statuses get updated automatically`, async ({ page }) => {
  
  await signIn(page);
  await uploadDocument(page);

  await page.goto("/documents");

  // Create a second file-status because the main one will be automatically removed when complete
  await page.evaluate(() => {
    const fileStatus = document.createElement("file-status");
    fileStatus.dataset.id = document.querySelector("file-status").dataset.id;
    document.body.appendChild(fileStatus);
  });

  await expect(page.locator("file-status").nth(1)).toHaveText("Processing");
  expect(await page.locator("file-status").count()).toEqual(2);

  // wait until doc has completed
  await page.locator("file-status").nth(1).waitFor({ state: "detached" });

  expect(await page.locator("file-status").count()).toEqual(1);
  await expect(page.locator("file-status")).toHaveText("Complete");
  
});
