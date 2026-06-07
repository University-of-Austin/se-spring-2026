import { expect, test } from '@playwright/test';

// The full Gold-spec flow:
//   create user → switch to that user → post a message → see it in the feed → delete it
// We do create + switch as separate steps (sign out between them) so the
// "switch" assertion is real, not implicit in the auto-sign-in after create.
test('create → switch → post → see → delete', async ({ page }) => {
  const username = `e2e${Date.now().toString().slice(-9)}`;
  const message = `E2E test message at ${new Date().toISOString()}`;

  // ── 1. Create user ────────────────────────────────────────────────────────
  await page.goto('/login');

  const createForm = page.locator('form').filter({ hasText: 'Create a new account' });
  await createForm.getByLabel('Username').fill(username);
  await createForm.getByRole('button', { name: /create account/i }).click();

  await expect(page).toHaveURL('/');
  await expect(page.locator('.user-pill').filter({ hasText: `@${username}` })).toBeVisible();

  // ── 2. Sign out, then switch back to that user ────────────────────────────
  await page.goto('/login');
  await page.getByRole('button', { name: /sign out/i }).click();

  const switchForm = page.locator('form').filter({ hasText: 'Sign in as an existing user' });
  await switchForm.getByLabel('Username').fill(username);
  await switchForm.getByRole('button', { name: /sign in/i }).click();

  await expect(page).toHaveURL('/');
  await expect(page.locator('.user-pill').filter({ hasText: `@${username}` })).toBeVisible();

  // ── 3. Post a message ─────────────────────────────────────────────────────
  await page.getByLabel(/new post/i).fill(message);
  await page.getByRole('button', { name: 'Post', exact: true }).click();

  // ── 4. See it in the feed ─────────────────────────────────────────────────
  const postBody = page.locator('.card__body', { hasText: message });
  await expect(postBody).toBeVisible();

  // ── 5. Delete it ──────────────────────────────────────────────────────────
  const postCard = page.locator('article.card').filter({ hasText: message });
  await postCard.getByRole('button', { name: /delete post/i }).click();

  // Optimistic delete = immediate disappearance from UI.
  await expect(postBody).toHaveCount(0);
});

test('client-side validation: empty post disables submit', async ({ page }) => {
  const username = `val${Date.now().toString().slice(-9)}`;

  await page.goto('/login');
  const createForm = page.locator('form').filter({ hasText: 'Create a new account' });
  await createForm.getByLabel('Username').fill(username);
  await createForm.getByRole('button', { name: /create account/i }).click();
  await expect(page).toHaveURL('/');

  const submit = page.getByRole('button', { name: 'Post', exact: true });
  await expect(submit).toBeDisabled();

  await page.getByLabel(/new post/i).fill('hi');
  await expect(submit).toBeEnabled();
});

test('search syncs to ?q= URL param', async ({ page }) => {
  await page.goto('/');
  const searchInput = page.locator('[data-shortcut="search"]');
  await searchInput.fill('hello');
  // Debounced 300ms — wait a beat then check URL.
  await page.waitForTimeout(400);
  await expect(page).toHaveURL(/\?q=hello/);
});

// Cursor-pagination smoke test. PAGE_SIZE in useFeed is 20, so posting 22
// messages and clicking "Load more" exercises the cursor path end-to-end:
// frontend builds urlsafe-base64 cursor → A2 decodes it → returns
// CursorPage → frontend merges into the loaded list. Nothing else in the
// suite catches a broken cursor (unit tests mock the endpoints).
test('Load more fetches older posts via cursor pagination', async ({ page, request }) => {
  test.setTimeout(60_000);
  const username = `pg${Date.now().toString().slice(-9)}`;
  const apiBase = 'http://localhost:8000';

  // Create the user via the API (faster than going through the UI).
  await request.post(`${apiBase}/users`, { data: { username } });

  // Post 22 messages directly to the API. Sequential so id order is
  // predictable and we can assert which post falls past the first page.
  for (let i = 1; i <= 22; i++) {
    await request.post(`${apiBase}/posts`, {
      headers: { 'X-Username': username },
      data: { message: `pagination test post #${i} for ${username}` },
    });
  }

  // Sign in as that user (so the feed shows their posts).
  await page.goto('/login');
  const switchForm = page.locator('form').filter({ hasText: 'Sign in as an existing user' });
  await switchForm.getByLabel('Username').fill(username);
  await switchForm.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL('/');

  // Filter the feed to only this user's posts (search by the username
  // suffix in their messages — keeps the assertion deterministic against
  // a busy backend).
  const searchInput = page.locator('[data-shortcut="search"]');
  await searchInput.fill(username);
  await page.waitForTimeout(500);

  // First page (20 newest): post #22 should be visible, #1 should not.
  const newest = page.locator('.card__body').filter({ hasText: `#22 for ${username}` });
  const oldest = page.locator('.card__body').filter({ hasText: `#1 for ${username}` });
  await expect(newest).toBeVisible();
  await expect(oldest).toHaveCount(0);

  // Click "Load more" — this is the cursor request.
  await page.getByRole('button', { name: /load more/i }).click();

  // After load more, post #1 (the oldest) should be in the list.
  await expect(oldest).toBeVisible();
});

// Cross-tab delete race: another tab deletes a post, then you click Delete
// on the same post here. The server returns 404; the optimistic removal was
// correct, so the post must stay gone — not resurrect via rollback and then
// stick around because polling can't contradict a ghost.
test('deleting a post already removed elsewhere stays gone', async ({ page, request }) => {
  const username = `xtab${Date.now().toString().slice(-9)}`;
  const message = `cross-tab delete test ${Date.now()}`;
  const apiBase = 'http://localhost:8000';

  await request.post(`${apiBase}/users`, { data: { username } });
  const created = await request.post(`${apiBase}/posts`, {
    headers: { 'X-Username': username },
    data: { message },
  });
  const post = (await created.json()) as { id: number };

  // Sign in and confirm the post is on screen.
  await page.goto('/login');
  const switchForm = page.locator('form').filter({ hasText: 'Sign in as an existing user' });
  await switchForm.getByLabel('Username').fill(username);
  await switchForm.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL('/');

  const postBody = page.locator('.card__body').filter({ hasText: message });
  await expect(postBody).toBeVisible();

  // "Another tab" deletes it via the API directly.
  await request.delete(`${apiBase}/posts/${post.id}`);

  // Click Delete here — the DELETE will 404.
  const postCard = page.locator('article.card').filter({ hasText: message });
  await postCard.getByRole('button', { name: /delete post/i }).click();

  // Post is gone immediately and stays gone across a poll tick (5s) — no
  // rollback ghost.
  await expect(postBody).toHaveCount(0);
  await page.waitForTimeout(6000);
  await expect(postBody).toHaveCount(0);
});
