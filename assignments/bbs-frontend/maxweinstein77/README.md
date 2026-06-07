# BBS Frontend (Postack) by Max Weinstein

React + TypeScript + Vite frontend on top of my A2 BBS API.

## 1. How to run

You need to have two separate terminal windows open when running this. Terminal 1 serves as your A2 backend (FastAPI server on port 8000) and terminal 2 serves as your A4 frontend (React app on port 5173).

**Terminal 1: A2 backend**


```bash
cd assignments/bbs-webserver/maxweinstein77
# activate your venv however you set it up
uvicorn main:app --port 8000
```

**Terminal 2: A4 frontend**


```bash
cd assignments/bbs-frontend/maxweinstein77
npm install
npm run dev
```

Then launch `http://localhost:5173/` in your browser.

The backend URL is read from `VITE_API_BASE`. The `.env` file defaults it to `http://localhost:8000` so you don't need to set anything for local dev.

**Alterations I made to my A2 backend:** added the FastAPI `CORSMiddleware` to `main.py` so the frontend on `localhost:5173` can call the backend on `localhost:8000`. If we didn't have this in place, the browser would just block the requests. I also added a `GET /posts/{post_id}/reactions` endpoint (plus a `list_reactions_by_post` helper in `db.py`) so the frontend can render heart-reaction counts on each post.

## 2. Goal Tier

**Gold.** Bronze + silver + 2 of the 4 gold options:
- Real-time-ish updates (polling)
- One nontrivial UI feature (`@mentions` rendered as clickable links)

## 3. Design Strategy

**State and caching: React Query.** Claude initially suggested React Query because you end up with less boilerplate code. I pushed back since the lecture focused on the manual `useState`/`useEffect`/`try-catch-finally` pattern, and I wanted to try and implement it. The assignment asks for optimistic updates and polling, both of which are primary features in React Query (`useMutation` with `onMutate`/`onError`/`onSettled`, and `refetchInterval`). I utilized React Query, then wrapped all data fetching in small per-resource hooks (`useFeed`, `useUser`, `useCreatePost`, etc.) so the page components stay focused on rendering.

**Routing: flat URLs** `/posts/42`, `/users/alice`, not `/users/alice/posts/42`. Claude suggested the nested form since it has a more structured appearance but my A2 exposes posts as a flat resource (`GET /posts/{id}`), and the Feed renders posts whose author isn't always known at the very top. Flat URLs mirror the data model, make for cleaner links, and remain constant under the pressure of username changes if a user changes their username. Utilized `react-router-dom` for routing.

**Both optimistic post and delete.** I initially only wanted to incorporate optimistic delete since I thought optimistic posting would be deceiving since you want to actually know whether or not your post went through, optimizing for accuracy over speed. Put more concretely, you could very easily end up in a situation where 
you make a post and then you either refresh or go to a different page thinking that your post went through but you really have no way of confirming so because you have optimized for the UI speed. Consequently, you'll have assumed you made a post but it never actually posted. I ended up deciding on both optimistic posting and deleting because React Query handles the failure case by displaying an error message when a post doesn't go through in addition to the fact that most apps nowadays utilize optimistic posting. 

**Polling over push** A second query polls `GET /posts?limit=20&offset=0` every 3 seconds in the background. The displayed feed does NOT auto-refresh. Instead, new posts go into a sticky `"↑ N new posts"` banner. The user can click the banner to merge them in. The reason for this is that dropping content into the feed while someone is reading or scrolling is jarring and would make the user lose their reading position. The banner keeps the user in control. I picked polling over SSE/WebSockets because the assignment is a simple REST API and pushes would require backend work in my A2; polling at 3s comfortably meets the spec's "within ~5 seconds" target with an average delay of roughly 1.5s.

**X-Username handling** Claude initially suggested an Option A "Sign In" screen because it looks professional. I pushed back: X-Username isn't real auth, and pretending it is would mislead the user about whether their identity is protected. The actual flow is: first-time arrival shows a "Choose a username" screen; if the username already exists in the DB, we show a "Welcome back, alice. Is this you?" confirmation screen with a note that anyone can claim any name; new usernames are silently created. Once you're in, the header just says "Hello, username" with a switch button.

**File structure: hybrid (`api/`, `hooks/`, `components/`, `pages/`, `lib/`).** I considered a feature-based layout where each feature (`feed/`, `users/`, `posts/`) owned its own components, hooks, and API calls. The problem: shared bits like `<Loading />`, `<ErrorMessage />`, and `<PostRow />` get used by multiple features, so a pure feature layout breaks the moment two features share anything. The hybrid puts shared stuff at the top level by type and gives each page its own folder for page-specific bits making it more coherent and organized.

**CSS Modules** Claude suggested Tailwind for speed. I pushed back: Tailwind is an extra dependency and we also didn't cover it in that much detail during the lectures, and `className="flex items-center gap-2 p-4 ..."` strings make the JSX harder to reference. CSS Modules is built into Vite, scopes styles automatically, and is just plain CSS. I figured it would be a lot simpler and organized.

## 4. What role my agent played in the building process?

I used Claude as an intellectual sparring partner, suggesting ideas and pushing back on ideas that it suggested I implement. For example, I found it helpful in considering design decisions like picking React Query over manual state and picking CSS Modules over Tailwind. I pushed back on its suggestion for the routing structures of nested URLs because I thought flat would be better since they mirror the backend. As mentioned earlier, I think the agent was most helpful in really thinking through the design decision regarding around optimistic posting. I was concerned about deceiving users into thinking they had posted when in fact there was no way to confirm whether they really posted their post. The hardest thing I had to push Claude on was the loading and error states. Left to itself it would have shipped `data.map(...)` with no guard, so I had to scaffold the three-state pattern (loading / error / data) early and tell it to fill in the success state.

## 5. Test command

```bash
npm test
```

Runs 14 tests across 3 files using Vitest + React Testing Library: parser tests for `@mentions`, render and interaction tests for `<PostRow>`, and unit tests for the `formatRelativeTime` helper.

## Gold features

**(Almost) real-time updates:** A separate React Query polls `/posts` every 3 seconds with `refetchIntervalInBackground: false` (pauses when the tab is hidden). The Feed compares the polled result against what's currently rendered and shows a sticky banner with the count of new posts; clicking it refetches the feed and smooth-scrolls to the top. The user's own posts don't trigger the banner because the `posts-latest` query is invalidated right after a create or delete.

**`@mentions` rendered as clickable links.** The `Mentions` component parses any `@username` substring (3–20 word chars, same regex as A2's server-side rule) into a `<Link>` pointing at `/users/<username>`. Uses regex lookbehind/lookahead so `foo@bar.com` doesn't false-positive as a mention and `@toolongusernamehere` doesn't get truncated into a fake 20-char one. Rendered everywhere a post message is rendered (Feed, UserProfile, PostDetail) by going through the shared `<PostRow>` component.

**Bonus: heart reactions.** Beyond the two required gold picks, I added optimistic heart reactions on every post. Click the ♡ to react, click again to unreact, and hover for a tooltip listing who liked the post. This required adding a new `GET /posts/{post_id}/reactions` endpoint to my A2 backend (noted above).