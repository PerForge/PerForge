// browser_tests/tests/example.spec.js
const { test, expect } = require('@playwright/test');

test('Homepage has expected title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle("Register");
});