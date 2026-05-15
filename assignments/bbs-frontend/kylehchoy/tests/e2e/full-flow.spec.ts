import { test, expect, type Page } from '@playwright/test'

/**
 * End-to-end happy path the assignment lists as the gold-tier
 * Playwright bar:
 *
 *   create user → switch to that user → post a message → see it in
 *   the feed → delete it
 *
 * One spec, runs against the live frontend + a live A2 backend on
 * :8000. See playwright.config.ts for the orchestration story.
 *
 * Each run mints a fresh user (e2e_<base36-timestamp>) so the test
 * is idempotent across re-runs against the same SQLite db. The
 * "switch to that user" step is implicit — creating a user via the
 * sign-up flow auto-switches identity in this app (per A2's
 * "X-Username is preference, not auth" semantics).
 */
test.describe('thenetwork — full user flow', () => {
  let username: string
  let postBody: string

  test.beforeEach(({}, testInfo) => {
    // RFC: ^[a-zA-Z0-9_]{3,20}$ — base36 timestamp keeps us inside.
    username = `e2e_${Date.now().toString(36)}`
    postBody = `End-to-end smoke ${testInfo.title} ${Date.now()}`
  })

  test('create → post → see → delete', async ({ page }) => {
    // 0. Land on the Wall.
    await page.goto('/')
    await expect(page.getByRole('link', { name: 'thenetwork' })).toBeVisible()

    // 1. Create user via /signup.
    await page.goto('/signup')
    await page.getByLabel('Username').fill(username)
    await expect(page.getByRole('button', { name: /^claim name/i })).toBeEnabled()
    await page.getByRole('button', { name: /^claim name/i }).click()

    // Successful create redirects to the Wall.
    await expect(page).toHaveURL('/')

    // 2. Compose a post.
    const compose = page.getByLabel(/^Compose/)
    await expect(compose).toBeVisible()
    await compose.fill(postBody)
    await page.getByRole('button', { name: /^post/i }).click()

    // 3. See the post in the feed.
    // Optimistic insert makes the text appear immediately; the server
    // round-trip then replaces the temp row with the canonical one.
    await expect(page.getByText(postBody, { exact: true })).toBeVisible({
      timeout: 5_000,
    })
    // Eyebrow row should mention the new user.
    await expect(
      page.getByRole('link', { name: `@${username}` }).first(),
    ).toBeVisible()

    // 4. Open the thread for that specific post.
    // Find the article that contains our body, then click its
    // "Open thread" link.
    const article = page.locator('article').filter({ hasText: postBody }).first()
    await article.getByRole('link', { name: /open thread/i }).click()

    await expect(page).toHaveURL(/\/posts\/\d+$/)
    await expect(page.getByText(postBody, { exact: true })).toBeVisible()

    // 5. Delete via the two-click confirm pattern.
    await page.getByRole('button', { name: /^delete post$/i }).click()
    await page.getByRole('button', { name: /confirm delete/i }).click()

    // Redirects back to the Wall.
    await expect(page).toHaveURL('/')

    // 6. The post is gone from the Wall.
    await expect(page.getByText(postBody, { exact: true })).toHaveCount(0)
  })

  test('edit own post then see edited badge', async ({ page }) => {
    // 1. New identity + new post.
    await createUserAndIdentity(page, username)
    await composePost(page, postBody)
    await expect(page.getByText(postBody, { exact: true })).toBeVisible()

    // 2. Open the thread, edit the body.
    const article = page.locator('article').filter({ hasText: postBody }).first()
    await article.getByRole('link', { name: /open thread/i }).click()

    await page.getByRole('button', { name: /^edit post$/i }).click()
    const editor = page.getByLabel(/^editing/i)
    await editor.fill(postBody + ' [edited]')
    await page.getByRole('button', { name: /^save/i }).click()

    // 3. The edited content + edited-tag should render.
    await expect(
      page.getByText(postBody + ' [edited]', { exact: true }),
    ).toBeVisible()
    // Eyebrow on the detail view also shows an italic "edited Nm ago"
    // span — match by exact-text on a span so the body's "[edited]"
    // substring doesn't trip strict mode.
    await expect(page.locator('span', { hasText: /^edited / }).first()).toBeVisible()

    // 4. Back on the Wall, eyebrow has the "edited" italic.
    // Match the eyebrow span exactly (the body also contains the
    // substring "[edited]" so a fuzzy match would be ambiguous).
    await page.goto('/')
    const editedArticle = page.locator('article').filter({
      hasText: postBody + ' [edited]',
    }).first()
    await expect(editedArticle.getByText('edited', { exact: true })).toBeVisible()

    // Cleanup: delete the post so subsequent runs don't pile up.
    await editedArticle.getByRole('link', { name: /open thread/i }).click()
    await page.getByRole('button', { name: /^delete post$/i }).click()
    await page.getByRole('button', { name: /confirm delete/i }).click()
  })
})

async function createUserAndIdentity(page: Page, username: string) {
  await page.goto('/signup')
  await page.getByLabel('Username').fill(username)
  await page.getByRole('button', { name: /^claim name/i }).click()
  await expect(page).toHaveURL('/')
}

async function composePost(page: Page, body: string) {
  const compose = page.getByLabel(/^Compose/)
  await compose.fill(body)
  await page.getByRole('button', { name: /^post/i }).click()
}
