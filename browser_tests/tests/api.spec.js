// browser_tests/tests/api.spec.js
// Validates that core list API endpoints respond with HTTP 200 and expected JSON structure.
// Uses the authenticated storage from initial-setup.

const { test, expect } = require('@playwright/test');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');

// List endpoints to ping
const endpoints = [
  '/api/v1/secrets',
  '/api/v1/prompts',
  '/api/v1/nfrs',
  '/api/v1/graphs',
  '/api/v1/template-groups',
  '/api/v1/templates',
  '/api/v1/projects',
];

test.use({
  storageState: path.join(projectRoot, 'storageState.json'),
});

test.describe('API list/content endpoints', () => {
  let api;

  test.beforeAll(async ({ playwright }) => {
    api = await playwright.request.newContext({
      storageState: path.join(projectRoot, 'storageState.json'),
    });
  });

  test.afterAll(async () => {
    await api.dispose();
  });

  endpoints.forEach((url) => {
    test(`GET ${url}`, async () => {
      const response = await api.get(url);
      expect(response.ok()).toBeTruthy();
      const body = await response.json();
      // All API responses must have standard shape { status: 'success'|'error', ... }
      expect(body).toHaveProperty('status');
      expect(body.status).toBe('success');
      expect(body).toHaveProperty('data');
    });
  });
});
