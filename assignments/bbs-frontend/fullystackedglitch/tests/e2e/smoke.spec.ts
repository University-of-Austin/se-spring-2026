import { expect, test } from "@playwright/test";

// End-to-end smoke flow against a running A2 backend on :8000.
// The flow: create a fresh user → post a message → see it on feed + profile →
// refresh and confirm identity persists → delete the post via the detail view.
// Each run picks a unique username so tests don't collide with prior data.

const uniq = () => `e2e_${Date.now().toString(36)}`;

test.beforeEach(async ({ page }) => {
  // Start each test signed out so the routes that depend on identity behave
  // as a real new visitor would experience.
  await page.context().clearCookies();
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
});

test("sign up, post, see on feed and profile, refresh keeps identity, delete", async ({
  page,
}) => {
  const username = uniq();
  const message = `hello from ${username}`;

  await page.goto("/signup");
  // The compose form on / nags signed-out visitors to sign in, but the signup
  // page renders independently — start there.
  await page.getByPlaceholder(/3-20 chars/i).fill(username);
  await page.getByRole("button", { name: /create \+ sign in/i }).click();

  // Lands on feed after sign-up.
  await expect(page).toHaveURL("/");
  await expect(page.getByText(`signed in as`)).toBeVisible();
  await expect(page.getByRole("link", { name: `@${username}` })).toBeVisible();

  // Post a message via the textarea, which is the compose form on the feed.
  const textarea = page.getByRole("textbox", { name: /what's on your mind/i });
  await textarea.fill(message);
  await page.getByRole("button", { name: /^post$/i }).click();

  // The post shows up on the feed (optimistic prepend on page 1).
  await expect(
    page.getByRole("article", { name: `Post by ${username}` }),
  ).toContainText(message);

  // Drill into the user profile via the author link in the row.
  await page
    .getByRole("article", { name: `Post by ${username}` })
    .getByRole("link", { name: `@${username}` })
    .click();
  await expect(page).toHaveURL(`/users/${username}`);

  // The profile renders its own copy of the post row (without the author chip,
  // since the page header is the author). Scope inside main and assert on the
  // specific article rather than the page's `getByRole("article")`, which
  // would race against the previous view's articles during the transition.
  const profileArticle = page
    .locator("main")
    .getByRole("article", { name: `Post by ${username}` });
  await expect(profileArticle).toBeVisible();
  await expect(profileArticle).toContainText(message);

  // Identity survives a full refresh.
  await page.reload();
  await expect(page.getByText(`signed in as`)).toBeVisible();

  // Walk back to the feed and into the post detail to delete.
  await page.getByRole("link", { name: /^feed$/ }).click();
  await expect(page).toHaveURL("/");

  // The permalink is the timestamp link inside the row; match by its href
  // shape rather than the rendered timestamp text so the test doesn't break
  // when the local time format changes.
  await page
    .getByRole("article", { name: `Post by ${username}` })
    .locator('a[href^="/posts/"]')
    .click();
  await expect(page).toHaveURL(/\/posts\/\d+/);

  // The browser confirm() dialog auto-accepts.
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: /^delete$/i }).click();

  // Back on the feed; the post is gone.
  await expect(page).toHaveURL("/");
  await expect(page.getByText(message)).toHaveCount(0);
});

test("search filters the feed and survives a refresh via the URL", async ({
  page,
}) => {
  const username = uniq();
  const tag = `tag${Date.now().toString(36)}`;

  // Create a user and a single tagged post so we can search for it.
  await page.goto("/signup");
  await page.getByPlaceholder(/3-20 chars/i).fill(username);
  await page.getByRole("button", { name: /create \+ sign in/i }).click();

  await page.getByRole("textbox", { name: /what's on your mind/i }).fill(
    `searching for ${tag}`,
  );
  await page.getByRole("button", { name: /^post$/i }).click();
  await expect(page.getByText(`searching for ${tag}`)).toBeVisible();

  // Search box hits the URL after a debounce, then triggers a refetch.
  await page.getByRole("searchbox").fill(tag);
  await expect(page).toHaveURL(new RegExp(`q=${tag}`));
  await expect(page.getByText(`searching for ${tag}`)).toBeVisible();

  // Reload and confirm the URL state alone restores the query.
  await page.reload();
  await expect(page.getByRole("searchbox")).toHaveValue(tag);
  await expect(page.getByText(`searching for ${tag}`)).toBeVisible();
});

test("compose surfaces server validation when the post is empty-after-whitespace", async ({
  page,
}) => {
  const username = uniq();
  await page.goto("/signup");
  await page.getByPlaceholder(/3-20 chars/i).fill(username);
  await page.getByRole("button", { name: /create \+ sign in/i }).click();

  // Whitespace-only input: the client trims and disables submit, so the
  // button is unreachable without circumventing it. This documents the
  // disabled-state guard rather than the server's 422 path.
  await page
    .getByRole("textbox", { name: /what's on your mind/i })
    .fill("   ");
  await expect(page.getByRole("button", { name: /^post$/i })).toBeDisabled();
});

test("nonexistent user route renders the 404 view", async ({ page }) => {
  await page.goto("/users/definitely_not_a_real_user_xyz");
  await expect(page.getByRole("heading", { name: /user not found/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /back to users/i })).toBeVisible();
});

test("polling: a post made in tab A appears in tab B without a manual refresh", async ({
  browser,
}) => {
  // Two separate contexts so localStorage doesn't leak between them — they
  // act like two real users in two real browser tabs. Polling lives in the
  // feed and runs every 5s; this test gives it ~7s of headroom.
  const alice = await browser.newContext();
  const bob = await browser.newContext();
  try {
    const pageA = await alice.newPage();
    const pageB = await bob.newPage();

    const userA = uniq();
    const userB = `${uniq()}b`;
    const message = `realtime ping ${Date.now().toString(36)}`;

    // Sign up each user in their own context.
    for (const [page, name] of [[pageA, userA], [pageB, userB]] as const) {
      await page.goto("/signup");
      await page.getByPlaceholder(/3-20 chars/i).fill(name);
      await page.getByRole("button", { name: /create \+ sign in/i }).click();
      await expect(page).toHaveURL("/");
    }

    // Tab B is sitting on the feed before tab A posts. The message shouldn't
    // be there yet — it doesn't exist on the server yet.
    await expect(pageB.getByText(message)).toHaveCount(0);

    // Tab A posts.
    await pageA.getByRole("textbox", { name: /what's on your mind/i }).fill(
      message,
    );
    await pageA.getByRole("button", { name: /^post$/i }).click();
    await expect(pageA.getByText(message)).toBeVisible();

    // Tab B should pick the post up via background polling within one cycle
    // plus latency. 8s gives the 5s timer + network + render plenty of room.
    await expect(pageB.getByText(message)).toBeVisible({ timeout: 8000 });
  } finally {
    await alice.close();
    await bob.close();
  }
});

test("sign-in autocomplete suggests matches and rejects unknown names", async ({
  page,
}) => {
  // Seed a known user so we have something to match the combobox against
  // regardless of whatever data is already in the dev DB.
  const username = uniq();
  await page.goto("/signup");
  await page.getByPlaceholder(/3-20 chars/i).fill(username);
  await page.getByRole("button", { name: /create \+ sign in/i }).click();
  await expect(page).toHaveURL("/");

  // Sign out so we exercise the combobox as a returning visitor.
  await page.getByRole("button", { name: /switch user/i }).click();
  await expect(page).toHaveURL("/signup");

  const combobox = page.getByRole("combobox");
  await combobox.click();
  // Type the full unique suffix so we hit a single match — prior test runs
  // leave alphabetically-earlier `e2e_*` users behind that would otherwise
  // saturate the 8-suggestion cap.
  await combobox.fill(username);

  // The listbox should expose this user as an option.
  const option = page.getByRole("option", { name: new RegExp(`@${username}`) });
  await expect(option).toBeVisible();

  // Pressing Enter signs in to the highlighted option (the first match).
  await combobox.press("Enter");
  await expect(page).toHaveURL(`/users/${username}`);
  await expect(page.getByText(`signed in as`)).toBeVisible();

  // Typing a name that doesn't exist surfaces the inline error and doesn't
  // navigate or set localStorage.
  await page.getByRole("button", { name: /switch user/i }).click();
  await expect(page).toHaveURL("/signup");
  await page.getByRole("combobox").fill("ghost_no_such_user");
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: /no user named/i }),
  ).toBeVisible();
  await expect(page).toHaveURL("/signup");
});
