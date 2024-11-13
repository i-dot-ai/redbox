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
            console.error(error);
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

module.exports = {
  signIn,
  sendMessage,
};
