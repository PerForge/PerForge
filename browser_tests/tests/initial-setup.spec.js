// browser_tests/tests/initial-setup.spec.js
// End-to-end flow to register (if needed), log in, and create a new project.
// Run with: npm test  (see package.json) or `npx playwright test`

const { test, expect } = require('@playwright/test');
const path = require('path');

// Import Playwright config to read admin credentials
const projectRoot = path.resolve(__dirname, '..');
// eslint-disable-next-line node/no-missing-require
const { admin } = require(path.join(projectRoot, 'playwright.config'));

// Helper to get cookie by name
const getCookie = (cookies, name) => cookies.find((c) => c.name === name);

test.describe('First-time application setup', () => {
  test('Register admin (if necessary), log in, and create project', async ({ page, context }) => {
    // 1. Open application root. `baseURL` defined in Playwright config handles the host.
    await page.goto('/');

    // 2. Check if we landed on the admin-registration page.
    if (page.url().includes('/register-admin')) {
      await page.fill('input[name="user"], input[name="username"], #user, #username', admin.username);
      await page.fill('input[name="password"], #password', admin.password);
      // Submit and wait for navigation to login page
      await Promise.all([
        page.waitForURL(/\/login/, { timeout: 15_000 }),
        page.click('button[type="submit"], button[name="register"], button:has-text("Sign UP")')
      ]);
    }

    // 3. We should now be on the login page.
    expect(page.url()).toContain('/login');
    await page.fill('input[name="user"], input[name="username"], #user, #username', admin.username);
    await page.fill('input[name="password"], #password', admin.password);
    await Promise.all([
      page.waitForURL(/choose-project|\/$/, { timeout: 15_000 }),
      page.click('button[type="submit"], button[name="login"], button:has-text("Sign in")')
    ]);

    // 4. After login we expect to see "Choose your project" page
    //    Wait for either the heading text or the URL.
    await Promise.race([
      page.waitForSelector('h2:has-text("Choose your project")'),
      page.waitForURL(/choose-project/),
    ]);

    // 5. Cookie `session` must now be present.
    const cookiesAfterLogin = await context.cookies();
    expect(getCookie(cookiesAfterLogin, 'session')).toBeDefined();

    // 6. Create a unique project via the modal
    const uniqueProjectName = `autotest_${Date.now()}`;

    // Wait for and click the "new project" button which opens the modal
    await page.waitForSelector('button[data-bs-target="#projectModal"]');
    await page.click('button[data-bs-target="#projectModal"]');
    await page.waitForSelector('#projectModal.show');

    // Fill project name and tick default config checkbox
    await page.fill('#project_name', uniqueProjectName);
    await page.check('#create_examples');

    // Save project
    await page.click('#saveProject');

        // Wait for modal to close
    await page.waitForSelector('#projectModal', { state: 'hidden' });

    // The page is redirected to root; wait for network idle
    await page.waitForLoadState('networkidle');

    // Click newly created project card to set it active (cookies)
    await page.click(`.card-project a:has-text("${uniqueProjectName}")`);

    // Wait for cookies to be set via backend response
    await page.waitForTimeout(1000); // small pause to allow cookie writing

    // 7. Validate cookies for project context exist
    const cookiesAfterProject = await context.cookies();
    const projectCookie = getCookie(cookiesAfterProject, 'project');
    const projectNameCookie = getCookie(cookiesAfterProject, 'project_name');

    expect(projectCookie).toBeDefined();
    expect(projectNameCookie).toBeDefined();
    expect(projectNameCookie.value).toBe(uniqueProjectName);

    // Persist authenticated storage for subsequent tests
    await context.storageState({ path: path.join(projectRoot, 'storageState.json') });
  });
});
