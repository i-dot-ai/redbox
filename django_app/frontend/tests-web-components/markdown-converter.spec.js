import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`Markdown can be converted to HTML`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  // Markdown can be added
  await page.evaluate(() => {
    let converter = document.createElement("markdown-converter");
    document.body.appendChild(converter);
    converter.update("# Test heading");
  });
  await expect(page.locator("markdown-converter h3")).toHaveText("Test heading");

  // Markdown can be updated
  await page.evaluate(() => {
    let converter = document.querySelector("markdown-converter");
    converter.update("Test paragraph");
  });
  await expect(page.locator("markdown-converter p")).toHaveText("Test paragraph");

});
