const { test, signIn } = require("./utils.js");

test(`The Add File button opens the file-selector`, async ({ page }) => {
  await signIn(page);

  setTimeout(async () => {
    await page.getByText("Add file").click();
  }, 100);
  await page.waitForEvent("filechooser");

});
