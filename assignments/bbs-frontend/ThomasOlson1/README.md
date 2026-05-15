# BBS Frontend, A4

React + TypeScript + Vite frontend for my A2 BBS API.

## Tier: gold

Bronze and silver are both done. My two gold picks are:

- **Dark mode** that follows `prefers-color-scheme` on first load, lets you override it with a button or the `t` key, and remembers the choice in `localStorage`.
- **5-second polling** on the feed. While the tab is visible, `GET /posts` re-runs every 5 seconds and merges in new posts. Posts I've just submitted (still waiting on the server's response) are kept separate so the poll doesn't erase them before they're confirmed.

## A note on "toast"

I use the word **toast** a few times below. A toast is a small notification that pops up in the bottom-right corner of the page, stays for about 4 seconds, and disappears on its own. I use them for things like "Post deleted" or "Failed to save bio" so the user gets feedback without a modal interrupting them. The code is in `src/components/Toast.tsx`.

## How to run

```bash
npm install
npm run dev        # http://localhost:5173
npm test           # vitest, 12 tests
```

The backend URL comes from `VITE_API_BASE` and defaults to `http://localhost:8000`. There's a `.env.example` in this folder.

You also need the A2 backend running:

```bash
cd ../../bbs-webserver/ThomasOlson1
python3 -m uvicorn main:app --port 8000
```

### Changes I made to A2

I added FastAPI's `CORSMiddleware` to `main.py` allowing `http://localhost:5173`. Without it the browser refuses to let the React app read responses, because `:5173` (Vite) and `:8000` (uvicorn) are different origins. Nothing else changed. A2 still passes 129/129 in `verify_api.py`.

## How the fetches are structured

I wanted to be able to point at any fetch in the app and say exactly where it lives, so I split it into four layers. A component asks for data, that request travels down through the layers, the server responds, and the data travels back up.

**1. `src/api/client.ts`** is the only file that actually talks to the server. It wraps the browser's built-in fetch so every request is sent the same way: attaches the current username, sends and reads JSON, and if the server returns an error it pulls the human-readable message out so the UI can show it.

**2. `src/api/posts.ts` and `src/api/users.ts`** are the only files that know the URLs. Each function in them is one line that says "send this kind of request" by calling the wrapper above. If you want to find where the app posts a new message, it's `createPost` in `posts.ts`.

| File | Functions |
| --- | --- |
| `api/posts.ts` | `listPosts`, `getPost`, `createPost`, `deletePost`, `patchPost` |
| `api/users.ts` | `listUsers`, `getUser`, `getUserPosts`, `createUser`, `patchUser` |

**3. `src/hooks/`** are small reusable pieces of behavior that the page components can plug into. Each one packages up a pattern I would otherwise have to rewrite on every page.

| Hook | What it does |
| --- | --- |
| `useFetch` | Runs a fetch when a page loads and gives the page back three things: "is it still loading", "did it fail", and "here's the data". Also cancels the request if you navigate away mid-load, so a slow old response can't overwrite a fresh one. |
| `usePolling` | Re-runs a function on a timer, but only while the tab is in the foreground. The feed uses this to auto-refresh every 5 seconds. |
| `useDarkMode` | Remembers your theme choice, falls back to your system setting, and updates the page when you switch. |

**4. `src/pages/` and `src/components/`** are the actual screens. They ask the hooks for data and render either a spinner, an error message, or the content. When you do something (post, delete, edit), they call the matching function from layer 2 and update what is on screen.

The feed is the one page that doesn't use `useFetch`. It has to juggle three fetches at once (the first load, the 5-second poll, and "load more") plus the in-flight optimistic posts, so it keeps its own state directly instead of leaning on the generic hook.

The compose box is intentionally split out from the feed. It doesn't know how the feed stores its post list. It just tells the feed "here's a new post going out", "the server confirmed it", or "the server rejected it" by calling four small callbacks the feed gives it. That way the feed owns the list and compose owns the draft, and neither has to know about the other's internals.

## Design decisions

1. **I wrote `useFetch` instead of pulling in TanStack Query.** A library would hide the lifecycle inside a global cache, and I want to be able to read each page top-to-bottom and see where its data comes from. The cost is that I don't get free background revalidation, which is fine. The only place I actually wanted that was the feed, and there I opted in with `usePolling`.

2. **Optimistic UI for create and delete, conservative for PATCH.** Posting and deleting feel sluggish without it, so the feed updates instantly and rolls back with a toast (a small bottom-right notification, see the section above) on failure. PATCH (editing your bio, editing a post) happens inside a single-resource view where a "Saving…" disable is clearer than a flash of stale-then-updated text.

3. **`X-Username` is treated as identity, not auth.** The current username lives in `localStorage` and is exposed by `AuthContext`. A `storage` event listener keeps multiple tabs in sync. The UI is honest about not being real auth: the delete button is visible to non-authors, and if you click it on someone else's post the 403 from A2 comes back as a toast.

4. **Polling, not server push.** This is a BBS, not a chat app. A 5-second delay is fine, and a polling hook is one file. Adding SSE or websockets would mean a real chunk of A2 work for a feature that isn't worth that. The interval is gated by `document.visibilityState`, so a backgrounded tab is silent.

5. **Routing.** `react-router-dom` v7 with `BrowserRouter`. Every URL is bookmarkable and the back button works. When you visit `/users/ghost` directly, the page renders an inline "user not found" instead of bouncing you to `/404`. You got there from a real-looking link, so the URL should stay.

## Where my agent helped most and where I had to push back

Claude was good at the layered scaffolding once I told it the rule: no inline fetches, everything through `request<T>`. It produced the typed resource modules and the optimistic flow (negative temp ids, snapshot the list before deleting in case I need to restore it) without me having to spell it out.

I had to push back in three places. First, it wrote `useFetch` without an `AbortController`, which is the exact race the assignment warns about. Click between two profiles quickly and the slower response wins. I made it abort on cleanup and ignore `AbortError`. Second, it kept writing `if (loading) return null` on every page, which is the blank-screen-on-mount bug the assignment also warns about. I changed every page to render a `<Spinner />` on the first load and keep stale data on later refetches so the feed doesn't flash empty every poll tick. Third, it wanted to put the dark-mode class on `document.body`. I moved it to `documentElement.dataset.theme` so a single CSS file owns both themes via custom properties and nothing about colors leaks into JSX.

## Tests

```bash
npm test
```

12 tests across 3 files:

- `tests/apiClient.test.ts`: `request()` handles 200/204 responses, `{detail: "..."}` errors, the 422 validation-array shape, and sends `X-Username` when given one.
- `tests/AuthContext.test.tsx`: starts empty, hydrates from `localStorage`, persists on set/sign-out.
- `tests/Compose.test.tsx`: submit-disabled when empty, counter turns red past 500, locked sign-in prompt when no user is set, end-to-end submit fires the right HTTP request.

## Keyboard shortcuts

Press `?` in the app for the full panel. Highlights: `Cmd/Ctrl + Enter` to post, `/` to focus search, `g` then `h/u/s` to jump pages, `t` to toggle theme.
