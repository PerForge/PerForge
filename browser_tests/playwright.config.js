// browser_tests/playwright.config.js
const config = {
    testDir: './tests',
  
    use: {
      baseURL: process.env.BASE_URL || 'http://localhost:7878',
      browserName: 'chromium',
      headless: true,
    },
  };
  
  module.exports = config;