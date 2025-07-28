// browser_tests/playwright.config.js
const config = {
    projects: [
      {
        name: 'ui-setup',
        testMatch: /initial-setup\.spec\.js$/,
      },
      {
        name: 'navigation',
        testMatch: /navigation\.spec\.js$/,
        dependencies: ['ui-setup'],
      },
      {
        name: 'api',
        testMatch: /api\.spec\.js$/,
        dependencies: ['navigation'],
      },
    ],
    testDir: './tests',

    use: {
      baseURL: process.env.BASE_URL || 'http://localhost:7878',
      browserName: 'chromium',
      headless: true,
    },
    workers: 1,

    admin: {
      username: process.env.ADMIN_USERNAME || 'admin',
      password: process.env.ADMIN_PASSWORD || 'admin',
    },
  };

  module.exports = config;