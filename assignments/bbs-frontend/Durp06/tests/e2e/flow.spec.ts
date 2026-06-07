import { test, expect } from '@playwright/test';

// Full user flow: create user → switch to it → post → see in feed → delete.
// Each run generates a unique username so re-runs don't collide on the
// real backend DB. The post message is also unique for the same reason.
test('full user flow: signup, post, see, delete', async ({ page }) => {
  const unique = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const username = `e2e_${unique}`.slice(0, 20);
  const message = `hello from e2e ${unique}`;

  // Start fresh — don't carry an identity from previous test runs.
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());

  // 1) Sign up creates the user and switches identity.
  await page.goto('/signup');
  await page.getByLabel('Username').fill(username);
  await page.getByRole('button', { name: /create account/i }).click();
  await page.waitForURL('**/');
  await expect(page.getByRole('link', { name: `@${username}` })).toBeVisible();

  // 2) Compose a post.
  await page.goto('/compose');
  const ta = page.getByLabel(/message/i);
  await ta.fill(message);
  await page.getByRole('button', { name: /^post$/i }).click();
  await page.waitForURL('**/');

  // 3) The message appears in the feed.
  await expect(page.getByText(message)).toBeVisible();

  // 4) Delete the post. Find the article containing the message, then click its delete button.
  const article = page.locator('article.post', { hasText: message });
  await article.getByRole('button', { name: /delete post/i }).click();

  // 5) Post is gone.
  await expect(page.getByText(message)).toHaveCount(0);
});
