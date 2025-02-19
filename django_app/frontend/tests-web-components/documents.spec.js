const { test, expect, sendMessage, signIn, uploadDocument } = require("./utils.js");


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


test(`A document can be sent (and token sizes are checked)`, async ({ page }) => {

  const fileTokenSize = "30";

  await signIn(page);

  await expect(page.locator("file-status")).toHaveCount(0);
  await uploadDocument(page);
  await expect(page.locator("file-status")).toHaveCount(1);

  // sending the message before the document is uploaded should fail
  await sendMessage(page);
  await expect(page.locator("chat-message")).toContainText("You have files waiting to be processed. Please wait for these to complete and then send the message again.");

  // sending the message after the document is uploaded should succeed
  await expect(page.locator("file-status [data-tokens]")).toHaveAttribute("data-tokens", fileTokenSize);
  await expect(page.locator("file-status")).toHaveText("Complete test-upload.html");
  await sendMessage(page);
  await expect(page.locator(".rb-uploaded-docs__item")).toContainText("test-upload.html");
  await expect(page.locator(".rb-uploaded-docs__item")).toHaveAttribute("data-tokens", fileTokenSize);

  await expect(page.locator("file-status")).toHaveCount(0);

});