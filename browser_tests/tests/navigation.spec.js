// browser_tests/tests/navigation.spec.js
// Reuses authenticated storage from initial-setup.spec.js.
// Navigates across core application pages and verifies they load.

const { test, expect } = require('@playwright/test');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');

// Pages to verify
const pages = ['/', '/secrets', '/integrations', '/prompts', '/nfrs', '/graphs', '/templates'];

test.use({
  storageState: path.join(projectRoot, 'storageState.json'),
});

test.describe('Main navigation pages', () => {
  pages.forEach((url) => {
    test(`visit ${url}`, async ({ page }) => {
      const response = await page.goto(url);
      expect(response && response.ok()).toBeTruthy();
      // ensure page loaded some meaningful content
      await expect(page).toHaveTitle(/.+/);
    });
  });
});
