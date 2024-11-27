import { test, expect } from "@playwright/test";
const { exec } = require("child_process");
require("dotenv").config();

const signIn = async (page) => {
  await page.goto("/sign-in");

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
  await expect(page.locator("h1")).toContainText("My details");
};

const sendMessage = async (page) => {
  await page.locator(".iai-chat-input__input").fill("Testing");
  await page.getByRole("button", { name: "Send" }).click();
};

const uploadDocument = async (page) => {
  await page.goto("/upload");
  await page.setInputFiles('input[type="file"]', "./test-upload.html");
  await page.click('button[type="submit"]');
};

module.exports = {
  signIn,
  sendMessage,
  uploadDocument,
};
