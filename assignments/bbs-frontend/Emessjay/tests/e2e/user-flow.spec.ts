// End-to-end test for the gold-tier user flow:
//   create user → sign out → switch back via the dropdown → post →
//   see the post in the feed → click into detail → delete → confirm
//   it's gone.
//
// Each run uses a unique username + message so the test doesn't
// collide with previous runs (and so it can run in a polluted local
// DB without flaking).  A2 has no DELETE /users endpoint, so the
// test user is intentionally left behind; the message it created is
// cleaned up by the final DELETE.

import { test, expect } from "@playwright/test";

function uniqueSuffix(): string {
  // Time-ordered, URL-safe, no collisions across rapid reruns.
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

test("full flow: create user, switch to them, post, see in feed, delete", async ({ page }) => {
  const username = `e2e${uniqueSuffix()}`;
  const message = `e2e message ${uniqueSuffix()}`;

  // ─── Land on the feed ─────────────────────────────────────────
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Feed" })).toBeVisible();

  // ─── Create the user via the Identity page ────────────────────
  await page.getByRole("link", { name: "Identity" }).click();
  await expect(page).toHaveURL("/identity");

  await page.getByLabel("Username").fill(username);
  await page.getByRole("button", { name: /create user/i }).click();

  // On success the app navigates to / and the header shows the new
  // identity.  This *also* implicitly verifies create-then-be-that-user.
  await expect(page).toHaveURL("/");
  await expect(page.getByText(new RegExp(`posting as @${username}`))).toBeVisible();

  // ─── Sign out and then switch back via the dropdown ───────────
  // This is the explicit "switch to that user" beat from the
  // assignment's gold-tier requirement.
  await page.getByRole("link", { name: "Identity" }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  // Be specific: "Not signed in." (with period) is the IdentityView body
  // copy.  Without this, the header's "not signed in" status text also
  // matches and the strict-mode locator fails.
  await expect(page.getByText("Not signed in.")).toBeVisible();

  await page.getByLabel("Pick an existing user").selectOption(username);
  await page.getByRole("button", { name: "Use this name" }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByText(new RegExp(`posting as @${username}`))).toBeVisible();

  // ─── Post a message via Compose ───────────────────────────────
  // The nav link is labeled "Post" (the route is still /compose).
  await page.getByRole("link", { name: "Post" }).click();
  await expect(page).toHaveURL("/compose");

  await page.getByLabel("Message").fill(message);
  await page.getByRole("button", { name: "Post" }).click();

  // The optimistic-update layer drops us back on the feed
  // immediately.  We wait for the real (non-optimistic) entry to
  // land before clicking — the optimistic entry is a plain <article>
  // while the real entry from the server wraps the message in a
  // <Link> to /posts/{id}.  Checking for the Link specifically
  // avoids the brief window where both render the same message text.
  await expect(page).toHaveURL("/");
  const postLink = page.getByRole("link", { name: new RegExp(message) });
  await expect(postLink).toBeVisible({ timeout: 10_000 });

  // ─── Click into post detail ───────────────────────────────────
  // Use the Delete button (unique to PostDetailView) as the
  // readiness signal — it's only visible once the route transition
  // is complete AND the post has loaded.  Asserting the message
  // text here would race against the feed's optimistic+real entries
  // both rendering the same string during the React tick where the
  // routes swap.
  await postLink.click();
  await expect(page).toHaveURL(/\/posts\/\d+/);
  const deleteButton = page.getByRole("button", { name: "Delete" });
  await expect(deleteButton).toBeVisible();

  // ─── Delete the post (accepting the confirm dialog) ───────────
  page.once("dialog", (d) => d.accept());
  await deleteButton.click();

  // ─── Verify we're back on the feed and the post is gone ───────
  // Check the Link specifically (a real server post would render it).
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("link", { name: new RegExp(message) })).toHaveCount(0, {
    timeout: 10_000,
  });
});
