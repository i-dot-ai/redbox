import { test, expect } from "@playwright/test";
const { sendMessage, signIn } = require("./utils.js");

test(`The activity log is displayed`, async ({ page }) => {
  await signIn(page);

  await page.goto("/chats");

  await sendMessage(page);
  expect(page.getByText("You sent this prompt")).toBeVisible();

});
