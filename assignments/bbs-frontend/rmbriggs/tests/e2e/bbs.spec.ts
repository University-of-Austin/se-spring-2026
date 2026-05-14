import { test, expect } from "@playwright/test";

// Generate a unique-per-run username so tests don't collide with stale data.
const RUN_ID = Date.now().toString(36).slice(-6);

// The login page has two username inputs:
//   - id="switch"  → label text: "Username"  (sign in as existing user)
//   - id="create"  → label text: "Username (3–20 chars, letters/digits/underscore)"
// Use exact=true for the sign-in field so it doesn't match the create label.
const CREATE_LABEL = /Username \(3.20 chars/;

test.describe("BBS gold-tier user flow", () => {
  test("create user → switch → post → see in feed → delete", async ({ page }) => {
    const alice = `e2e_${RUN_ID}_a`;
    const bob = `e2e_${RUN_ID}_b`;
    const aliceMessage = `hello from ${alice} at ${Date.now()}`;

    // ─── 1. Land on home, signed-out state ───
    await page.goto("/");
    // The nav shows a lowercase "sign in" link when logged out.
    await expect(page.getByRole("link", { name: "sign in", exact: true })).toBeVisible();

    // ─── 2. Create user alice via /login ───
    await page.getByRole("link", { name: "sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByLabel(CREATE_LABEL).fill(alice);
    await page.getByRole("button", { name: "Create" }).click();

    // ─── 3. Redirected home, "signed in as alice" visible ───
    await expect(page).toHaveURL("/");
    await expect(page.getByText(/signed in as/i)).toBeVisible();
    await expect(page.getByRole("link", { name: alice })).toBeVisible();

    // ─── 4. Create user bob then switch identity back to alice ───
    await page.goto("/login");
    // Create bob — use the "create" form (bottom section).
    await page.getByLabel(CREATE_LABEL).fill(bob);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL("/");
    await expect(page.getByRole("link", { name: bob })).toBeVisible();

    // Switch back to alice via the existing-user sign-in form.
    // The sign-in label is "Username" (exact match, id="switch").
    await page.goto("/login");
    await page.getByLabel("Username", { exact: true }).fill(alice);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL("/");
    await expect(page.getByRole("link", { name: alice })).toBeVisible();

    // ─── 5. Post a message as alice ───
    // ComposeBox label is "Message" (sr-only, htmlFor="compose-message").
    await page.getByLabel("Message").fill(aliceMessage);
    await page.getByRole("button", { name: /^post$/i }).click();

    // ─── 6. See the message in the feed ───
    const card = page.locator("article").filter({ hasText: aliceMessage }).first();
    await expect(card).toBeVisible({ timeout: 10_000 });
    // Confirm the card is committed (not optimistic pending) by waiting for the
    // delete button, which only renders when isOwner && !pending.
    await expect(card.getByRole("button", { name: "delete" })).toBeVisible({ timeout: 10_000 });

    // ─── 7. Delete the post via the inline delete button ───
    await card.getByRole("button", { name: "delete" }).click();

    // The post should be removed from the feed.
    await expect(
      page.locator("article").filter({ hasText: aliceMessage }),
    ).toHaveCount(0, { timeout: 5_000 });
  });

  test("422 from server is surfaced inline in ComposeBox", async ({ page }) => {
    const username = `e2e_${RUN_ID}_v`;
    await page.goto("/login");
    await page.getByLabel(CREATE_LABEL).fill(username);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL("/");

    // Intercept POST /posts and return a 422 so we don't need to bypass the
    // client-side disabled-state guard (which is correct behavior). This tests
    // that ComposeBox correctly surfaces server-side validation errors.
    await page.route("**/posts", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            detail: [
              {
                type: "string_too_long",
                loc: ["body", "message"],
                msg: "String should have at most 500 characters",
                ctx: { max_length: 500 },
              },
            ],
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Post a valid short message — the route intercept returns a 422.
    await page.getByLabel("Message").fill("trigger 422");
    await page.getByRole("button", { name: /^post$/i }).click();

    // ComposeBox renders a role="alert" div with the formatted error detail.
    const alert = page.getByRole("alert");
    await expect(alert).toBeVisible({ timeout: 5_000 });
    await expect(alert).toContainText(/character|too long|500/i);
  });

  test("reaction count updates optimistically then settles", async ({ page }) => {
    const username = `e2e_${RUN_ID}_r`;
    const message = `react me ${Date.now()}`;
    await page.goto("/login");
    await page.getByLabel(CREATE_LABEL).fill(username);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page).toHaveURL("/");

    await page.getByLabel("Message").fill(message);
    await page.getByRole("button", { name: /^post$/i }).click();

    const card = page.locator("article").filter({ hasText: message }).first();
    await expect(card).toBeVisible({ timeout: 10_000 });
    // Wait for the committed card (delete button only appears on non-pending owner posts).
    await expect(card.getByRole("button", { name: "delete" })).toBeVisible({ timeout: 10_000 });

    // Click ♥ — the count for that kind on this card should become "1".
    const heartButton = card.getByRole("button", { name: "heart" });
    await heartButton.click();
    await expect(heartButton).toContainText("1", { timeout: 3_000 });

    // Switch to 🔥 — heart should drop back to 0, fire becomes 1.
    const fireButton = card.getByRole("button", { name: "fire" });
    await fireButton.click();
    await expect(heartButton).toContainText("0", { timeout: 3_000 });
    await expect(fireButton).toContainText("1", { timeout: 3_000 });

    // Clean up: delete the post.
    await card.getByRole("button", { name: "delete" }).click();
    await expect(
      page.locator("article").filter({ hasText: message }),
    ).toHaveCount(0, { timeout: 5_000 });
  });
});
