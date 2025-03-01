import { test as base, expect } from "@playwright/test";
const { exec } = require("child_process");
require("dotenv").config();


// Fail test if any console errors are detected
const test = base.extend({
  page: async ({ page }, use) => {

    let consoleErrors = 0;
    page.on("console", msg => {
      if (msg.type() === "error") {
        consoleErrors++;
      }
    });

    await use(page);

    expect(consoleErrors).toBe(0);

  }
});


const signIn = async (page) => {
  await page.goto("/log-in");

  // Perform login actions
  await page.fill("#email", process.env.FROM_EMAIL);
  await page.click('button[type="submit"]');

  const getMagicLink = () => {
    return new Promise((resolve) => {
      exec(
        `poetry run python ../../manage.py show_magiclink_url ${process.env.FROM_EMAIL}`,
        async (error, stdout, stderr) => {
          if (error) {
            throw new Error(
              `There was a problem getting the magic-link. Please ensure you have set FROM_EMAIL in your env file and created a user for ${process.env.FROM_EMAIL}`
            );
          }
          resolve(stdout);
        }
      );
    });
  };

  const magicLink = await getMagicLink();

  await page.goto(`${magicLink}`);
  await expect(page.locator(".chat-options__heading")).toContainText("What would you like to ask?");
};

const sendMessage = async (page, message) => {
  await page.locator(".rb-chat-input textarea").fill(message || "Testing");
  await page.getByRole("button", { name: "Send" }).click();
};

const uploadDocument = async (page) => {
  await page.waitForSelector('input[type="file"]', { state: 'attached' });
  await page.setInputFiles('input[type="file"]', "./test-upload.html");
  const fileStatus = page.locator("file-status");
  await fileStatus.waitFor();
};

module.exports = {
  signIn,
  sendMessage,
  uploadDocument,
  test,
  expect,
};
