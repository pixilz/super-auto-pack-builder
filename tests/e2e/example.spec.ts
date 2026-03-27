import { test, expect } from '@playwright/test';

test('Page has a title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle('Super Auto Pack Builder');
});