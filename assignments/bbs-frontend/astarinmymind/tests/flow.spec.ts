// End-to-end Playwright spec covering the gold-required user flow:
//   create user → sign in as that user → post → see in feed → delete.
// Each test uses a unique username so the spec is re-runnable without
// having to clean up the backend database between runs.

import { test, expect } from '@playwright/test'

// Helper: short unique username that satisfies the A2 regex /^[a-zA-Z0-9_]+$/
// and the 3-20 char length limit. We base it on the current millis so two
// concurrent runs (or fast re-runs) can't collide.
function uniqueUser(prefix = 'e2e'): string {
  return `${prefix}_${Date.now().toString().slice(-8)}`
}

test('create user → sign in → post → appears in feed → delete', async ({ page }) => {
  const username = uniqueUser()
  const message = `playwright says hi ${username}`

  // Create the user via the sign-in page's "Create new user" form.
  await page.goto('/signin')
  await page.getByLabel('New username').fill(username)
  await page.getByRole('button', { name: 'Create user' }).click()

  // After creation we should be back on the feed, signed in as the new user.
  // The header's identity link reads "@<username>".
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('link', { name: `@${username}` })).toBeVisible()

  // Post a message via the compose form.
  await page.getByPlaceholder(`What's on your mind, @${username}?`).fill(message)
  await page.getByRole('button', { name: 'Post' }).click()

  // The new post should appear in the feed at the top.
  await expect(page.getByText(message)).toBeVisible()

  // Click into the post detail page (stretched-link covers the article).
  await page.getByRole('link', { name: /Open post #/ }).first().click()
  await expect(page).toHaveURL(/\/posts\/\d+/)
  await expect(page.getByText(message)).toBeVisible()

  // Delete it. window.confirm() defaults to OK in Playwright via this handler.
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete' }).click()

  // After delete we navigate back to the feed; the message should be gone.
  await expect(page).toHaveURL('/')
  await expect(page.getByText(message)).toHaveCount(0)
})

test('switch user: sign out then sign in as a different existing user', async ({ page }) => {
  // Create two users via the API directly so we have two known signed-in
  // identities to switch between. Going through the UI for the first user
  // is already covered by the test above.
  const userA = uniqueUser('swa')
  const userB = uniqueUser('swb')

  for (const name of [userA, userB]) {
    const res = await page.request.post('http://localhost:8000/users', {
      data: { username: name },
    })
    expect(res.ok()).toBeTruthy()
  }

  // Sign in as userA via the existing-user form.
  await page.goto('/signin')
  await page.getByLabel('Username', { exact: true }).fill(userA)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('link', { name: `@${userA}` })).toBeVisible()

  // Sign out and switch to userB.
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL('/signin')

  await page.getByLabel('Username', { exact: true }).fill(userB)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('link', { name: `@${userB}` })).toBeVisible()
  await expect(page.getByRole('link', { name: `@${userA}` })).toHaveCount(0)
})

test('user list and user profile routes are reachable', async ({ page }) => {
  await page.goto('/users')
  // The page shows an h1 "Users" — find it explicitly so we don't match the
  // nav link of the same text.
  await expect(page.getByRole('heading', { name: 'Users', level: 1 })).toBeVisible()

  // Click the first @username link in the list and land on their profile.
  const firstUser = page.locator('main a[href^="/users/"]').first()
  const href = await firstUser.getAttribute('href')
  await firstUser.click()
  await expect(page).toHaveURL(href!)
})

test('unknown user shows the 404 view', async ({ page }) => {
  await page.goto('/users/definitely_not_a_real_user_xyz')
  await expect(page.getByRole('heading', { name: 'User not found' })).toBeVisible()
})

test('signed-in identity persists across a full page reload (localStorage)', async ({ page }) => {
  // Bronze requires "stay logged in across refresh" via localStorage. Prove it:
  // sign in, hard reload the page, confirm the header still shows @<user>.
  const username = uniqueUser('persist')
  await page.request.post('http://localhost:8000/users', { data: { username } })

  await page.goto('/signin')
  await page.getByLabel('Username', { exact: true }).fill(username)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('link', { name: `@${username}` })).toBeVisible()

  await page.reload()
  await expect(page.getByRole('link', { name: `@${username}` })).toBeVisible()
})

test('Post button is disabled when the compose textarea is empty', async ({ page }) => {
  // Bronze: client-side validation should prevent posting an empty message.
  const username = uniqueUser('empty')
  await page.request.post('http://localhost:8000/users', { data: { username } })

  await page.goto('/signin')
  await page.getByLabel('Username', { exact: true }).fill(username)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()

  const postBtn = page.getByRole('button', { name: 'Post' })
  await expect(postBtn).toBeDisabled()

  // Typing should re-enable it.
  await page.getByPlaceholder(`What's on your mind, @${username}?`).fill('not empty')
  await expect(postBtn).toBeEnabled()
})

test('theme choice persists across reload (gold B)', async ({ page }) => {
  // Visit fresh, force light mode by clearing the storage key first so the
  // test is deterministic regardless of the OS prefers-color-scheme.
  await page.goto('/')
  await page.evaluate(() => localStorage.removeItem('theme-pref'))
  await page.reload()

  // Click the toggle once. We don't know whether the initial state was light
  // or dark (depends on OS), so just assert that the post-toggle state
  // survives a reload — that's what "persists" means.
  await page.getByRole('button', { name: /Switch to (light|dark) mode/ }).click()
  const themeAfterClick = await page.evaluate(() => document.documentElement.classList.contains('dark'))

  await page.reload()
  const themeAfterReload = await page.evaluate(() => document.documentElement.classList.contains('dark'))
  expect(themeAfterReload).toBe(themeAfterClick)
})

test('Cmd+Enter inside the compose textarea posts the message', async ({ page }) => {
  // Silver requires Cmd+Enter as the post shortcut. Test that it actually fires
  // a POST and the message appears in the feed without clicking the button.
  const username = uniqueUser('cmd')
  const message = `cmd-enter test ${username}`
  await page.request.post('http://localhost:8000/users', { data: { username } })

  await page.goto('/signin')
  await page.getByLabel('Username', { exact: true }).fill(username)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()

  const textarea = page.getByPlaceholder(`What's on your mind, @${username}?`)
  await textarea.fill(message)
  // Meta+Enter on Mac, Control+Enter elsewhere — both branches are handled in
  // ComposeForm's keydown listener, so either keystroke is a valid test.
  await textarea.press('Meta+Enter')

  await expect(page.getByText(message)).toBeVisible()
})

test('pressing ? opens the keyboard shortcut overlay', async ({ page }) => {
  // Silver requires a visible keyboard shortcut beyond Cmd+Enter. Ours is `?`.
  await page.goto('/')
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await page.keyboard.press('?')
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Keyboard shortcuts' })).toBeVisible()

  // Esc closes it.
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
})
