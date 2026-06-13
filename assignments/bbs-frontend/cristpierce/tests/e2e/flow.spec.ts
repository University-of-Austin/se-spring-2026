import { test, expect, type Page } from '@playwright/test'

/*
 * End-to-end user flow, run against the REAL frontend (npm run dev, started by
 * playwright.config.ts) with the API faithfully emulated at the network layer.
 *
 * Mocking the API here (rather than booting uvicorn) keeps the test hermetic and
 * deterministic — it runs with a single `npm run test:e2e`, no Python, no DB,
 * no shared state between runs — while still exercising the entire frontend:
 * routing, identity persistence, the composer, optimistic updates, and delete.
 */

interface MockPost {
  id: number
  username: string
  message: string
  created_at: string
  updated_at: string | null
}
interface MockUser {
  username: string
  created_at: string
  bio: string | null
  post_count: number
}

function ts(offsetSeconds: number): string {
  // Deterministic, lexicographically-ordered timestamps (no real clock needed).
  const base = new Date('2026-06-08T12:00:00.000Z').getTime()
  return new Date(base + offsetSeconds * 1000).toISOString()
}

async function installApiMock(page: Page) {
  const users: MockUser[] = []
  const posts: MockPost[] = []
  let nextId = 1
  let clock = 0

  const json = (status: number, body: unknown) =>
    ({ status, contentType: 'application/json', body: JSON.stringify(body) })
  const noContent = () => ({ status: 204, body: '' })

  await page.route(
    (url) => url.hostname === 'localhost' && url.port === '8000',
    async (route) => {
      const req = route.request()
      const u = new URL(req.url())
      const path = u.pathname
      const method = req.method()
      const body = req.postData() ? JSON.parse(req.postData() as string) : {}

      // POST /users
      if (method === 'POST' && path === '/users') {
        if (users.some((x) => x.username === body.username)) {
          return route.fulfill(json(409, { detail: 'Username already exists' }))
        }
        const user: MockUser = {
          username: body.username,
          created_at: ts(clock++),
          bio: null,
          post_count: 0,
        }
        users.push(user)
        return route.fulfill(json(201, user))
      }

      // GET /users
      if (method === 'GET' && path === '/users') return route.fulfill(json(200, users))

      // GET /users/:name and /users/:name/posts
      const userPosts = path.match(/^\/users\/([^/]+)\/posts$/)
      if (method === 'GET' && userPosts) {
        const name = decodeURIComponent(userPosts[1])
        return route.fulfill(
          json(200, posts.filter((p) => p.username === name).sort((a, b) => b.id - a.id)),
        )
      }
      const userOne = path.match(/^\/users\/([^/]+)$/)
      if (method === 'GET' && userOne) {
        const name = decodeURIComponent(userOne[1])
        const user = users.find((x) => x.username === name)
        if (!user) return route.fulfill(json(404, { detail: 'User not found' }))
        return route.fulfill(
          json(200, { ...user, post_count: posts.filter((p) => p.username === name).length }),
        )
      }

      // POST /posts
      if (method === 'POST' && path === '/posts') {
        const username = req.headers()['x-username']
        if (!username) return route.fulfill(json(400, { detail: 'X-Username header is required' }))
        const post: MockPost = {
          id: nextId++,
          username,
          message: body.message,
          created_at: ts(clock++),
          updated_at: null,
        }
        posts.unshift(post)
        return route.fulfill(json(201, post))
      }

      // GET /posts (+ ?q=)
      if (method === 'GET' && path === '/posts') {
        const q = u.searchParams.get('q')
        let result = [...posts].sort((a, b) => b.id - a.id)
        if (q) result = result.filter((p) => p.message.toLowerCase().includes(q.toLowerCase()))
        return route.fulfill(json(200, result))
      }

      // GET /feed (polling) — no live updates needed for this flow
      if (method === 'GET' && path === '/feed') return route.fulfill(json(200, []))

      // GET / DELETE /posts/:id
      const postOne = path.match(/^\/posts\/(\d+)$/)
      if (postOne) {
        const id = Number(postOne[1])
        if (method === 'GET') {
          const post = posts.find((p) => p.id === id)
          return post
            ? route.fulfill(json(200, post))
            : route.fulfill(json(404, { detail: 'Post not found' }))
        }
        if (method === 'DELETE') {
          const idx = posts.findIndex((p) => p.id === id)
          if (idx === -1) return route.fulfill(json(404, { detail: 'Post not found' }))
          posts.splice(idx, 1)
          return route.fulfill(noContent())
        }
      }

      // Reactions
      const reactAdd = path.match(/^\/posts\/(\d+)\/reactions$/)
      if (method === 'POST' && reactAdd) {
        return route.fulfill(json(201, { post_id: Number(reactAdd[1]), ...body }))
      }
      if (method === 'DELETE' && /^\/posts\/(\d+)\/reactions\/[^/]+$/.test(path)) {
        return route.fulfill(noContent())
      }

      return route.fulfill(json(200, []))
    },
  )
}

test('create a user, switch to them, post, see it in the feed, then delete it', async ({
  page,
}) => {
  await installApiMock(page)

  // Create + sign in as a new user.
  await page.goto('/login')
  await page.getByLabel('Username').fill('e2e_alice')
  await page.getByRole('button', { name: /create.*sign in/i }).click()

  // Identity persists and is shown in the header.
  await expect(page.getByTitle(/Signed in as e2e_alice/)).toBeVisible()

  // Compose a post and see it appear in the feed. Scope to the post <article>
  // so the assertion isn't ambiguous with the composer's textarea value during
  // the brief optimistic window.
  const message = 'hello from the end to end flow'
  const postCard = page.getByRole('article').filter({ hasText: message })
  await page.getByRole('textbox').fill(message)
  await page.getByRole('button', { name: /^post$/i }).click()
  await expect(postCard).toBeVisible()

  // Identity survives a refresh (localStorage).
  await page.reload()
  await expect(page.getByTitle(/Signed in as e2e_alice/)).toBeVisible()
  await expect(postCard).toBeVisible()

  // Delete it through the confirm dialog; it disappears.
  await page.getByRole('button', { name: 'Delete post' }).first().click()
  await page.getByRole('button', { name: 'Delete', exact: true }).click()
  await expect(postCard).toHaveCount(0)
})

test('search filters the feed by query', async ({ page }) => {
  await installApiMock(page)

  await page.goto('/login')
  await page.getByLabel('Username').fill('e2e_bob')
  await page.getByRole('button', { name: /create.*sign in/i }).click()
  await expect(page.getByTitle(/Signed in as e2e_bob/)).toBeVisible()

  const applesCard = page.getByRole('article').filter({ hasText: 'apples are great' })
  const orangesCard = page.getByRole('article').filter({ hasText: 'oranges are better' })

  const textarea = page.getByRole('textbox')
  await textarea.fill('apples are great')
  await page.getByRole('button', { name: /^post$/i }).click()
  await expect(applesCard).toBeVisible()

  await textarea.fill('oranges are better')
  await page.getByRole('button', { name: /^post$/i }).click()
  await expect(orangesCard).toBeVisible()

  // Searching narrows the feed to matching posts.
  await page.getByRole('searchbox').fill('apples')
  await expect(applesCard).toBeVisible()
  await expect(orangesCard).toHaveCount(0)
})
