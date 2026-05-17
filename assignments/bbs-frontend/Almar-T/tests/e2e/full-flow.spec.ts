import { expect, test } from "@playwright/test";

/**
 * End-to-end happy path covering every gradeable user action:
 *   1. create a new user (unique per run, so reruns don't 409)
 *   2. verify localStorage persistence by reloading mid-flow
 *   3. compose a post and see it in the feed (optimistic + reconciled)
 *   4. delete the post and confirm it's gone
 *
 * Requires the A2 backend on http://localhost:8000 with CORS enabled.
 * The Vite dev server is managed by playwright.config.ts.
 */

const stamp = `e2e_${Date.now()}`.slice(0, 20);

test("create user, post, see in feed, delete", async ({ page }) => {
  await page.goto("/sign-in");

  // ── Create new user ───────────────────────────────────────────
  const createSection = page.getByRole("heading", { name: "Create new user" })
    .locator("xpath=..");
  await createSection
    .getByLabel(/new username/i)
    .fill(stamp);
  await createSection
    .getByRole("button", { name: /create \+ sign in/i })
    .click();

  // Lands on feed, header shows @username chip
  await expect(page).toHaveURL("/");
  const chip = page.getByRole("link", { name: `Your profile: ${stamp}` });
  await expect(chip).toBeVisible();

  // ── Verify localStorage persistence across reload ────────────
  await page.reload();
  await expect(chip).toBeVisible();

  // ── Compose a post ───────────────────────────────────────────
  const message = `playwright says hi at ${new Date().toISOString()}`;
  await page.getByRole("textbox").fill(message);
  await page.getByRole("button", { name: /post message/i }).click();

  // Post appears in the feed (scope to the post list so the textarea
  // contents don't double-match while the API call is in flight)
  const postsList = page.getByRole("list").first();
  await expect(postsList.getByText(message)).toBeVisible();

  // Wait for optimistic reconcile — the dashed border (aria-busy) clears
  await expect(
    page.locator('article[aria-busy="true"]'),
  ).toHaveCount(0, { timeout: 5000 });

  // ── Survive a navigation away and back ──────────────────────
  await page.goto("/users");
  await page.goto("/");
  await expect(postsList.getByText(message)).toBeVisible();

  // ── Delete the post (handle the confirm() dialog) ────────────
  page.once("dialog", (d) => d.accept());
  // The delete button label is "Delete post {id}" via aria-label; there's
  // only one post we just created, but multiple may exist from other users.
  // Find the article containing our message and click its delete button.
  const article = page
    .locator("article")
    .filter({ hasText: message })
    .first();
  await article.getByRole("button", { name: /^delete/i }).click();

  // It's gone from the feed
  await expect(page.getByText(message)).toHaveCount(0);

  // A success toast appears
  await expect(page.getByText(/post deleted/i)).toBeVisible();
});

test("404 view on unknown user", async ({ page }) => {
  await page.goto("/users/definitely_not_a_real_user_xyz");
  await expect(page.getByRole("heading", { name: /user not found/i })).toBeVisible();
});

test("client-side validation blocks over-long posts", async ({ page }) => {
  // Each test gets a fresh browser context — sign in by creating a new user.
  const u = `e2e_v_${Date.now()}`.slice(0, 20);
  await page.goto("/sign-in");
  await page.getByLabel(/new username/i).fill(u);
  await page.getByRole("button", { name: /create \+ sign in/i }).click();
  await expect(page).toHaveURL("/");

  await page.getByRole("textbox").fill("a".repeat(501));
  await expect(page.getByText("501/500")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /post message/i }),
  ).toBeDisabled();
});
