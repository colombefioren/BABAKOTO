import { expect, test } from '@playwright/test';

test('playground shows the start button and captions region', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Babakoto' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Start conversation' })).toBeEnabled();
  await expect(page.getByRole('heading', { name: 'Transcript' })).toBeVisible();
  await expect(page.getByText('Nothing said yet.')).toBeVisible();
  await expect(page.getByTestId('latency-p50')).toHaveText('n/a');
});

test('starting without a LiveKit server configured shows a clear error', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await expect(page.locator('p[role="alert"]')).toContainText('Missing environment variables');
  await expect(page.getByRole('button', { name: 'Start conversation' })).toBeEnabled();
});

test('unauthenticated requests cannot open the playground or mint tokens', async ({ baseURL }) => {
  // Node fetch has no browser context from which to inherit the operator credentials.
  const page = await fetch(new URL('/', baseURL));
  const endpoint = await fetch(new URL('/api/token', baseURL), { method: 'POST' });
  for (const response of [page, endpoint]) {
    expect(response.status, response.url).toBe(401);
    expect(response.headers.get('www-authenticate')).toMatch(/^Basic realm=/);
    expect(response.headers.get('cache-control')).toContain('no-store');
  }
});
