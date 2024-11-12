import { test, expect } from "@playwright/test";
const { exec } = require("child_process");

module.exports = async (page) => {
  await page.goto("/sign-in");

  // Perform login actions
  const email = "test@test.com";
  await page.fill("#email", email);
  await page.click('button[type="submit"]');

  const getMagicLink = () => {
    return new Promise((resolve) => {
      exec(
        `poetry run python ../../manage.py createsuperuser --noinput --email ${email}`,
        (error, stdout, stderr) => {
          exec(
            `poetry run python ../../manage.py show_magiclink_url ${email}`,
            async (error, stdout, stderr) => {
              resolve(stdout);
            }
          );
        }
      );
    });
  };

  const magicLink = await getMagicLink();

  await page.goto(`${magicLink}`);
  await expect(page.locator("h1")).toContainText("My details");
};
