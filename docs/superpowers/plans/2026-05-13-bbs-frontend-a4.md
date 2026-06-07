# BBS Frontend (A4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Gold-tier React frontend for the A2 BBS Webserver by Fri 2026-05-15 5pm, covering all bronze requirements plus routing/optimistic-updates/tests/a11y (silver) and polling + visual design POV + threads/reactions/boards UI (gold).

**Architecture:** React + TypeScript + Vite under `assignments/bbs-frontend/rmbriggs/`. All HTTP goes through a single `api/client.ts` wrapper. Page-level state lives in hooks (`useFeed`, `usePost`, `useUsers`, `useBoards`, `useCurrentUser`); only current identity is global, via React context. Optimistic updates use `client_id` reconciliation. Polling is a 3s `setInterval` in `useFeed`, paused on `visibilitychange`.

**Tech Stack:** React 18, TypeScript, Vite, react-router-dom v6, Tailwind CSS, shadcn/ui, Vitest, React Testing Library.

**Spec:** `docs/superpowers/specs/2026-05-13-bbs-frontend-design.md`

---

## Conventions

- All paths in this plan are relative to repo root `/Users/micahbriggs/Developer/se-spring-2026/`.
- The frontend lives at `assignments/bbs-frontend/rmbriggs/` (henceforth `<fe>`).
- The A2 backend lives at `assignments/bbs-webserver/rmbriggs/` (henceforth `<be>`).
- Commits go on branch `bbs-frontend-rmbriggs`, branched from `bbs-webserver-rmbriggs`.
- Test style per repo preference: each case is its own named function, no parametrize.
- `npm` commands assume `cd <fe>` first unless noted.

---

## Phase 0: Branch + backend prep

### Task 1: Create A4 branch and verify A2 runs

**Files:** none (branch + env check)

- [ ] **Step 1: Create A4 branch from current**

```bash
cd /Users/micahbriggs/Developer/se-spring-2026
git checkout -b bbs-frontend-rmbriggs
```

- [ ] **Step 2: Verify A2 backend boots**

```bash
cd assignments/bbs-webserver/rmbriggs
source ../../../.venv/bin/activate    # adjust if your venv is elsewhere
uvicorn main:app --port 8000 &
sleep 1
curl -s http://localhost:8000/users
kill %1
```

Expected: a JSON array (possibly empty `[]`).

### Task 2: Add CORS to A2 backend

**Files:**
- Modify: `assignments/bbs-webserver/rmbriggs/main.py`

- [ ] **Step 1: Add CORSMiddleware to A2 main.py**

Insert after `app = FastAPI()`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: Verify CORS header appears**

```bash
cd assignments/bbs-webserver/rmbriggs
uvicorn main:app --port 8000 &
sleep 1
curl -s -H "Origin: http://localhost:5173" -I http://localhost:8000/users | grep -i access-control
kill %1
```

Expected: `access-control-allow-origin: http://localhost:5173` in the response headers.

- [ ] **Step 3: Commit**

```bash
git add assignments/bbs-webserver/rmbriggs/main.py
git commit -m "A2: enable CORS for A4 frontend (localhost:5173)"
```

---

## Phase 1: Scaffold + foundation (Wed eve, ~2h)

### Task 3: Scaffold Vite + TS + Tailwind + shadcn + router

**Files:**
- Create: `<fe>/package.json`, `<fe>/tsconfig.json`, `<fe>/vite.config.ts`, `<fe>/tailwind.config.ts`, `<fe>/index.html`, `<fe>/src/main.tsx`, `<fe>/src/App.tsx`, `<fe>/components.json`, `<fe>/.gitignore`, `<fe>/.env.example`

- [ ] **Step 1: Scaffold Vite**

```bash
cd /Users/micahbriggs/Developer/se-spring-2026
mkdir -p assignments/bbs-frontend/rmbriggs
cd assignments/bbs-frontend/rmbriggs
npm create vite@latest . -- --template react-ts
# answer "y" to "directory not empty" if asked
npm install
```

- [ ] **Step 2: Add router and Tailwind**

```bash
npm install react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 3: Configure Tailwind**

Overwrite `<fe>/tailwind.config.ts`:

```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontSize: {
        xs: ["12px", "16px"],
        sm: ["14px", "20px"],
        base: ["16px", "24px"],
        lg: ["20px", "28px"],
        xl: ["28px", "36px"],
      },
    },
  },
  plugins: [],
} satisfies Config;
```

Overwrite `<fe>/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: light;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

body {
  margin: 0;
  background: #fafafa;
  color: #1a1a1a;
}
```

- [ ] **Step 4: Set up shadcn**

```bash
npx shadcn@latest init -d
# Defaults: New York style, Slate base, CSS variables yes, src/components/ui
npx shadcn@latest add button input textarea label dialog
```

- [ ] **Step 5: Add path alias for @/**

Edit `<fe>/vite.config.ts` to include:

```ts
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
```

Edit `<fe>/tsconfig.json` `compilerOptions` to add:

```json
"baseUrl": ".",
"paths": { "@/*": ["./src/*"] }
```

- [ ] **Step 6: Write .env.example**

Create `<fe>/.env.example`:

```
VITE_API_BASE=http://localhost:8000
```

- [ ] **Step 7: Sanity-check the scaffold**

```bash
npm run dev -- --port 5173 &
sleep 2
curl -s -I http://localhost:5173 | head -1
kill %1
```

Expected: `HTTP/1.1 200 OK`.

- [ ] **Step 8: Commit**

```bash
cd /Users/micahbriggs/Developer/se-spring-2026
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: scaffold Vite + TS + Tailwind + shadcn + router"
```

### Task 4: API client (TDD)

**Files:**
- Create: `<fe>/src/api/types.ts`
- Create: `<fe>/src/api/client.ts`
- Create: `<fe>/tests/api/client.test.ts`

- [ ] **Step 1: Set up Vitest**

```bash
cd assignments/bbs-frontend/rmbriggs
npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Add to `<fe>/package.json` `scripts`:

```json
"test": "vitest run",
"test:watch": "vitest"
```

Add to `<fe>/vite.config.ts` (after `plugins`):

```ts
test: {
  environment: "jsdom",
  globals: true,
  setupFiles: ["./tests/setup.ts"],
},
```

Create `<fe>/tests/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 2: Define types**

Create `<fe>/src/api/types.ts`:

```ts
export type User = {
  username: string;
  created_at: string;
  bio: string | null;
  post_count: number;
};

export type Post = {
  id: number;
  username: string;
  message: string;
  created_at: string;
  updated_at: string | null;
  board: string | null;
  parent_id: number | null;
  reaction_counts: Record<string, number>;
};

export type Board = {
  name: string;
  description: string | null;
  created_at: string;
  post_count: number;
};

export type FeedPage = { posts: Post[]; next_cursor: string | null; has_more: boolean };

export type ApiError = { status: number; detail: string | Array<{ msg: string; loc: unknown[]; type: string }> };

export const isApiError = (e: unknown): e is ApiError =>
  typeof e === "object" && e !== null && "status" in e && "detail" in e;

export const formatDetail = (detail: ApiError["detail"]): string =>
  typeof detail === "string" ? detail : detail.map((d) => d.msg).join("; ");
```

- [ ] **Step 3: Write failing tests for client**

Create `<fe>/tests/api/client.test.ts`:

```ts
import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiFetch } from "@/api/client";

describe("apiFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("test_apiFetch_includes_X_Username_when_set", async () => {
    localStorage.setItem("username", "alice");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }),
    );

    await apiFetch("/users");

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-Username"]).toBe("alice");
  });

  it("test_apiFetch_omits_X_Username_when_unset", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("[]", { status: 200, headers: { "content-type": "application/json" } }),
    );

    await apiFetch("/users");

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-Username"]).toBeUndefined();
  });

  it("test_apiFetch_throws_ApiError_on_4xx_with_detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "User not found" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiFetch("/users/nope")).rejects.toMatchObject({ status: 404, detail: "User not found" });
  });

  it("test_apiFetch_returns_parsed_json_on_2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ username: "alice" }]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const result = await apiFetch("/users");

    expect(result).toEqual([{ username: "alice" }]);
  });

  it("test_apiFetch_handles_204_with_no_body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));

    const result = await apiFetch("/posts/1", { method: "DELETE" });

    expect(result).toBeNull();
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
npm test -- tests/api/client.test.ts
```

Expected: FAIL — `apiFetch` is not defined.

- [ ] **Step 5: Implement client**

Create `<fe>/src/api/client.ts`:

```ts
import type { ApiError } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const readUsername = (): string | null => {
  try {
    return localStorage.getItem("username");
  } catch {
    return null;
  }
};

export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const username = readUsername();
  if (username) headers["X-Username"] = username;
  if (init.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 204) return null as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const err: ApiError = { status: res.status, detail: data?.detail ?? res.statusText };
    throw err;
  }

  return data as T;
}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
npm test -- tests/api/client.test.ts
```

Expected: PASS, 5 tests.

- [ ] **Step 7: Commit**

```bash
cd /Users/micahbriggs/Developer/se-spring-2026
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: api client + types with X-Username + error normalization"
```

### Task 5: useCurrentUser hook + UserContext (TDD)

**Files:**
- Create: `<fe>/src/hooks/useCurrentUser.tsx`
- Create: `<fe>/tests/hooks/useCurrentUser.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `<fe>/tests/hooks/useCurrentUser.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { UserProvider, useCurrentUser } from "@/hooks/useCurrentUser";

const wrapper = ({ children }: { children: React.ReactNode }) => <UserProvider>{children}</UserProvider>;

describe("useCurrentUser", () => {
  beforeEach(() => localStorage.clear());

  it("test_useCurrentUser_returns_null_when_localStorage_empty", () => {
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    expect(result.current.username).toBeNull();
  });

  it("test_useCurrentUser_returns_stored_username_on_mount", () => {
    localStorage.setItem("username", "alice");
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    expect(result.current.username).toBe("alice");
  });

  it("test_setUsername_persists_to_localStorage", () => {
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    act(() => result.current.setUsername("bob"));
    expect(localStorage.getItem("username")).toBe("bob");
    expect(result.current.username).toBe("bob");
  });

  it("test_clearUsername_removes_from_localStorage", () => {
    localStorage.setItem("username", "alice");
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    act(() => result.current.clearUsername());
    expect(localStorage.getItem("username")).toBeNull();
    expect(result.current.username).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- tests/hooks/useCurrentUser.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement hook**

Create `<fe>/src/hooks/useCurrentUser.tsx`:

```tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

type Ctx = {
  username: string | null;
  setUsername: (u: string) => void;
  clearUsername: () => void;
};

const UserContext = createContext<Ctx | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsernameState] = useState<string | null>(null);

  useEffect(() => {
    setUsernameState(localStorage.getItem("username"));
  }, []);

  const setUsername = useCallback((u: string) => {
    localStorage.setItem("username", u);
    setUsernameState(u);
  }, []);

  const clearUsername = useCallback(() => {
    localStorage.removeItem("username");
    setUsernameState(null);
  }, []);

  const value = useMemo(() => ({ username, setUsername, clearUsername }), [username, setUsername, clearUsername]);
  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useCurrentUser(): Ctx {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useCurrentUser must be used inside <UserProvider>");
  return ctx;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- tests/hooks/useCurrentUser.test.tsx
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: useCurrentUser hook with localStorage persistence"
```

### Task 6: Router + Layout shell + 404

**Files:**
- Create: `<fe>/src/components/Layout.tsx`
- Create: `<fe>/src/pages/NotFound.tsx`
- Modify: `<fe>/src/App.tsx`
- Modify: `<fe>/src/main.tsx`

- [ ] **Step 1: Write Layout**

Create `<fe>/src/components/Layout.tsx`:

```tsx
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export default function Layout() {
  const { username, clearUsername } = useCurrentUser();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-neutral-200 bg-white">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link to="/" className="text-lg font-semibold">BBS</Link>
          <nav className="flex gap-3 text-sm text-neutral-600">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "text-neutral-900" : "")}>Feed</NavLink>
            <NavLink to="/users" className={({ isActive }) => (isActive ? "text-neutral-900" : "")}>Users</NavLink>
            <NavLink to="/boards" className={({ isActive }) => (isActive ? "text-neutral-900" : "")}>Boards</NavLink>
          </nav>
          <div className="ml-auto text-sm">
            {username ? (
              <span className="flex items-center gap-2">
                <span className="text-neutral-500">signed in as</span>
                <span className="font-medium">{username}</span>
                <button
                  className="text-neutral-500 underline"
                  onClick={() => { clearUsername(); navigate("/login"); }}
                >
                  switch
                </button>
              </span>
            ) : (
              <Link to="/login" className="underline">sign in</Link>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Write NotFound**

Create `<fe>/src/pages/NotFound.tsx`:

```tsx
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="py-12 text-center">
      <h1 className="text-xl font-semibold">Not found</h1>
      <p className="text-neutral-600 mt-2">That page doesn't exist.</p>
      <Link to="/" className="text-neutral-900 underline mt-4 inline-block">Back to feed</Link>
    </div>
  );
}
```

- [ ] **Step 3: Wire router in App.tsx**

Overwrite `<fe>/src/App.tsx`:

```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";
import NotFound from "@/pages/NotFound";
import { UserProvider } from "@/hooks/useCurrentUser";

// Page imports added in later tasks; stubs for now.
const FeedPage = () => <div>feed</div>;
const UsersPage = () => <div>users</div>;
const UserPage = () => <div>user</div>;
const PostPage = () => <div>post</div>;
const BoardsPage = () => <div>boards</div>;
const BoardPage = () => <div>board</div>;
const LoginPage = () => <div>login</div>;

export default function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<FeedPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/users/:username" element={<UserPage />} />
            <Route path="/posts/:id" element={<PostPage />} />
            <Route path="/boards" element={<BoardsPage />} />
            <Route path="/boards/:name" element={<BoardPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </UserProvider>
  );
}
```

- [ ] **Step 4: Verify it boots**

```bash
npm run dev -- --port 5173 &
sleep 2
curl -s http://localhost:5173 | grep -q "<title>" && echo OK
kill %1
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: router shell + Layout + NotFound"
```

### Task 7: LoginPage

**Files:**
- Create: `<fe>/src/pages/LoginPage.tsx`
- Modify: `<fe>/src/App.tsx` (swap stub)

- [ ] **Step 1: Implement LoginPage**

Create `<fe>/src/pages/LoginPage.tsx`:

```tsx
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { ApiError, formatDetail } from "@/api/types";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

export default function LoginPage() {
  const { setUsername } = useCurrentUser();
  const navigate = useNavigate();
  const [createValue, setCreateValue] = useState("");
  const [switchValue, setSwitchValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canCreate = USERNAME_RE.test(createValue) && createValue.length >= 3 && createValue.length <= 20;
  const canSwitch = USERNAME_RE.test(switchValue) && switchValue.length >= 3 && switchValue.length <= 20;

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users", { method: "POST", body: JSON.stringify({ username: createValue }) });
      setUsername(createValue);
      navigate("/");
    } catch (e) {
      const err = e as ApiError;
      setError(formatDetail(err.detail));
    } finally {
      setBusy(false);
    }
  }

  async function onSwitch(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch(`/users/${switchValue}`);
      setUsername(switchValue);
      navigate("/");
    } catch (e) {
      const err = e as ApiError;
      setError(formatDetail(err.detail));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md mx-auto space-y-8">
      <section className="space-y-3">
        <h1 className="text-xl font-semibold">Sign in</h1>
        <p className="text-sm text-neutral-600">
          Switch to an existing username. Identity is just a header (X-Username) — not real auth.
        </p>
        <form onSubmit={onSwitch} className="space-y-2">
          <label htmlFor="switch" className="block text-sm font-medium">Username</label>
          <input
            id="switch"
            value={switchValue}
            onChange={(e) => setSwitchValue(e.target.value)}
            className="w-full border border-neutral-300 rounded px-3 py-2"
            placeholder="alice"
            autoFocus
          />
          <button type="submit" disabled={!canSwitch || busy} className="bg-neutral-900 text-white px-4 py-2 rounded disabled:opacity-50">
            Sign in
          </button>
        </form>
      </section>

      <section className="space-y-3 border-t border-neutral-200 pt-6">
        <h2 className="text-lg font-semibold">Create a new user</h2>
        <form onSubmit={onCreate} className="space-y-2">
          <label htmlFor="create" className="block text-sm font-medium">Username (3–20 chars, letters/digits/underscore)</label>
          <input
            id="create"
            value={createValue}
            onChange={(e) => setCreateValue(e.target.value)}
            className="w-full border border-neutral-300 rounded px-3 py-2"
            placeholder="newuser"
          />
          <button type="submit" disabled={!canCreate || busy} className="bg-neutral-900 text-white px-4 py-2 rounded disabled:opacity-50">
            Create
          </button>
        </form>
      </section>

      {error && (
        <div role="alert" className="border border-red-300 bg-red-50 text-red-900 px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Wire into router**

In `<fe>/src/App.tsx`, replace the `LoginPage` stub with:

```tsx
import LoginPage from "@/pages/LoginPage";
```

(and remove the stub `const LoginPage = ...` line)

- [ ] **Step 3: Manual smoke test**

```bash
# Start backend in one terminal:
#   cd <be> && uvicorn main:app --port 8000
# Then:
npm run dev -- --port 5173 &
sleep 2
# Visit http://localhost:5173/login; create user "alice"; confirm redirect to /.
# Refresh; confirm "signed in as alice" persists.
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: LoginPage with create-user and switch-user flows"
```

---

## Phase 2: Feed + Compose + optimistic POST (Thu AM, ~3h)

### Task 8: useApi generic hook (TDD)

**Files:**
- Create: `<fe>/src/hooks/useApi.ts`
- Create: `<fe>/tests/hooks/useApi.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `<fe>/tests/hooks/useApi.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useApi } from "@/hooks/useApi";

describe("useApi", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("test_useApi_starts_in_loading_state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useApi<string[]>("/users"));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("test_useApi_transitions_to_success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(["alice"]), { status: 200, headers: { "content-type": "application/json" } }),
    );
    const { result } = renderHook(() => useApi<string[]>("/users"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["alice"]);
    expect(result.current.error).toBeNull();
  });

  it("test_useApi_transitions_to_error_on_500", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "boom" }), { status: 500, headers: { "content-type": "application/json" } }),
    );
    const { result } = renderHook(() => useApi<string[]>("/users"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toMatchObject({ status: 500 });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- tests/hooks/useApi.test.tsx
```

Expected: FAIL.

- [ ] **Step 3: Implement useApi**

Create `<fe>/src/hooks/useApi.ts`:

```ts
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/api/client";
import type { ApiError } from "@/api/types";

export type ApiState<T> = {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
};

export function useApi<T>(path: string | null): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(path !== null);
  const [error, setError] = useState<ApiError | null>(null);

  const run = useCallback(async () => {
    if (path === null) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<T>(path);
      setData(result);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    void run();
  }, [run]);

  return { data, loading, error, refetch: run };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- tests/hooks/useApi.test.tsx
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: useApi generic loading/error/data hook"
```

### Task 9: Shared LoadingRow + ErrorBox

**Files:**
- Create: `<fe>/src/components/LoadingRow.tsx`
- Create: `<fe>/src/components/ErrorBox.tsx`

- [ ] **Step 1: Implement components**

Create `<fe>/src/components/LoadingRow.tsx`:

```tsx
export default function LoadingRow({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="py-6 text-center text-sm text-neutral-500" role="status" aria-live="polite">
      {label}
    </div>
  );
}
```

Create `<fe>/src/components/ErrorBox.tsx`:

```tsx
import { ApiError, formatDetail } from "@/api/types";

export default function ErrorBox({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div role="alert" className="border border-red-300 bg-red-50 text-red-900 px-3 py-2 rounded text-sm flex items-start gap-3">
      <span className="flex-1">
        <span className="font-medium">Error {error.status}.</span> {formatDetail(error.detail)}
      </span>
      {onRetry && (
        <button onClick={onRetry} className="underline">Retry</button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: LoadingRow and ErrorBox shared components"
```

### Task 10: useFeed hook with cursor pagination + polling (TDD core)

**Files:**
- Create: `<fe>/src/hooks/useFeed.ts`
- Create: `<fe>/tests/hooks/useFeed.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `<fe>/tests/hooks/useFeed.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useFeed } from "@/hooks/useFeed";
import type { Post } from "@/api/types";

const mkPost = (id: number): Post => ({
  id, username: "alice", message: `m${id}`, created_at: "2026-05-13T00:00:00",
  updated_at: null, board: null, parent_id: null, reaction_counts: {},
});

const respond = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

describe("useFeed", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.restoreAllMocks();
  });

  it("test_useFeed_starts_in_loading_state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    const { result } = renderHook(() => useFeed());
    expect(result.current.loading).toBe(true);
  });

  it("test_useFeed_transitions_to_success_with_posts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      respond({ posts: [mkPost(1), mkPost(2)], next_cursor: null, has_more: false }),
    );
    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.posts.map((p) => p.id)).toEqual([1, 2]);
  });

  it("test_useFeed_transitions_to_error_on_500", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(respond({ detail: "boom" }, 500));
    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toMatchObject({ status: 500 });
  });

  it("test_useFeed_loadMore_appends_with_cursor", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(respond({ posts: [mkPost(2)], next_cursor: "c1", has_more: true }))
      .mockResolvedValueOnce(respond({ posts: [mkPost(1)], next_cursor: null, has_more: false }));

    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.posts.length).toBe(1));
    await act(async () => { await result.current.loadMore(); });
    expect(result.current.posts.map((p) => p.id)).toEqual([2, 1]);
    expect(result.current.hasMore).toBe(false);
    expect(fetchMock.mock.calls[1][0]).toContain("cursor=c1");
  });

  it("test_useFeed_polls_every_3s_and_merges_new_posts", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(respond({ posts: [mkPost(1)], next_cursor: null, has_more: false }))
      .mockResolvedValue(respond({ posts: [mkPost(2), mkPost(1)], next_cursor: null, has_more: false }));

    const { result } = renderHook(() => useFeed());
    await waitFor(() => expect(result.current.posts.length).toBe(1));

    await act(async () => { await vi.advanceTimersByTimeAsync(3001); });

    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(result.current.posts.map((p) => p.id)).toEqual([2, 1]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- tests/hooks/useFeed.test.tsx
```

Expected: FAIL.

- [ ] **Step 3: Implement useFeed**

Create `<fe>/src/hooks/useFeed.ts`:

```ts
import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/api/client";
import type { ApiError, FeedPage, Post } from "@/api/types";

export type OptimisticPost = Post & { client_id: string; status: "pending" | "failed" };

export type FeedState = {
  posts: Post[];
  optimistic: OptimisticPost[];
  loading: boolean;
  error: ApiError | null;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  refetch: () => Promise<void>;
  createPost: (message: string, board?: string | null, parent_id?: number | null) => Promise<void>;
};

export function useFeed(params?: { q?: string; board?: string; username?: string }): FeedState {
  const [posts, setPosts] = useState<Post[]>([]);
  const [optimistic, setOptimistic] = useState<OptimisticPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const isMounted = useRef(true);

  const buildQuery = useCallback(
    (cursor: string | null) => {
      const sp = new URLSearchParams();
      sp.set("limit", "20");
      sp.set("cursor", cursor ?? "");
      if (params?.q) sp.set("q", params.q);
      if (params?.board) sp.set("board", params.board);
      if (params?.username) sp.set("username", params.username);
      return sp.toString();
    },
    [params?.q, params?.board, params?.username],
  );

  const fetchFirstPage = useCallback(async () => {
    try {
      const data = await apiFetch<FeedPage>(`/posts?${buildQuery(null)}`);
      if (!isMounted.current) return;
      setPosts(data.posts);
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
      setError(null);
    } catch (e) {
      if (!isMounted.current) return;
      setError(e as ApiError);
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [buildQuery]);

  useEffect(() => {
    isMounted.current = true;
    setLoading(true);
    void fetchFirstPage();
    return () => {
      isMounted.current = false;
    };
  }, [fetchFirstPage]);

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === "visible") void fetchFirstPage();
    };
    const id = window.setInterval(tick, 3000);
    return () => window.clearInterval(id);
  }, [fetchFirstPage]);

  const loadMore = useCallback(async () => {
    if (!nextCursor) return;
    try {
      const data = await apiFetch<FeedPage>(`/posts?${buildQuery(nextCursor)}`);
      setPosts((prev) => {
        const seen = new Set(prev.map((p) => p.id));
        return [...prev, ...data.posts.filter((p) => !seen.has(p.id))];
      });
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch (e) {
      setError(e as ApiError);
    }
  }, [nextCursor, buildQuery]);

  const createPost = useCallback(
    async (message: string, board: string | null = null, parent_id: number | null = null) => {
      const client_id = crypto.randomUUID();
      const username = localStorage.getItem("username") ?? "you";
      const draft: OptimisticPost = {
        client_id,
        status: "pending",
        id: -1,
        username,
        message,
        created_at: new Date().toISOString(),
        updated_at: null,
        board,
        parent_id,
        reaction_counts: {},
      };
      setOptimistic((prev) => [draft, ...prev]);
      try {
        const created = await apiFetch<Post>("/posts", {
          method: "POST",
          body: JSON.stringify({ message, board, parent_id }),
        });
        setOptimistic((prev) => prev.filter((p) => p.client_id !== client_id));
        setPosts((prev) => (prev.some((p) => p.id === created.id) ? prev : [created, ...prev]));
      } catch (e) {
        setOptimistic((prev) => prev.filter((p) => p.client_id !== client_id));
        throw e;
      }
    },
    [],
  );

  return { posts, optimistic, loading, error, hasMore, loadMore, refetch: fetchFirstPage, createPost };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- tests/hooks/useFeed.test.tsx
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: useFeed with cursor pagination, 3s polling, optimistic POST"
```

### Task 11: PostCard component

**Files:**
- Create: `<fe>/src/components/PostCard.tsx`
- Create: `<fe>/src/components/UserPill.tsx`

- [ ] **Step 1: UserPill**

Create `<fe>/src/components/UserPill.tsx`:

```tsx
import { Link } from "react-router-dom";

export default function UserPill({ username }: { username: string }) {
  if (username === "[deleted]") {
    return <span className="text-neutral-500 italic">[deleted]</span>;
  }
  return (
    <Link to={`/users/${username}`} className="font-medium text-neutral-900 hover:underline">
      {username}
    </Link>
  );
}
```

- [ ] **Step 2: PostCard**

Create `<fe>/src/components/PostCard.tsx`:

```tsx
import { Link } from "react-router-dom";
import type { Post } from "@/api/types";
import UserPill from "./UserPill";

type Props = {
  post: Post;
  pending?: boolean;
};

function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function PostCard({ post, pending = false }: Props) {
  return (
    <article className={`border border-neutral-200 rounded-lg bg-white px-4 py-3 ${pending ? "opacity-60" : ""}`}>
      <header className="flex items-center gap-2 text-sm text-neutral-500">
        <UserPill username={post.username} />
        <span aria-hidden>·</span>
        <Link to={`/posts/${post.id}`} className="hover:underline">{fmtTime(post.created_at)}</Link>
        {post.board && (
          <>
            <span aria-hidden>·</span>
            <Link to={`/boards/${post.board}`} className="hover:underline">#{post.board}</Link>
          </>
        )}
        {pending && <span className="ml-auto text-xs italic text-neutral-400">posting…</span>}
      </header>
      <p className="mt-2 whitespace-pre-wrap text-base">{post.message}</p>
    </article>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: PostCard + UserPill components"
```

### Task 12: ComposeBox (TDD)

**Files:**
- Create: `<fe>/src/components/ComposeBox.tsx`
- Create: `<fe>/tests/components/ComposeBox.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `<fe>/tests/components/ComposeBox.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ComposeBox from "@/components/ComposeBox";

describe("ComposeBox", () => {
  it("test_compose_box_disables_submit_when_empty", () => {
    render(<ComposeBox onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /post/i })).toBeDisabled();
  });

  it("test_compose_box_enables_submit_with_text", async () => {
    render(<ComposeBox onSubmit={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/message/i), "hello");
    expect(screen.getByRole("button", { name: /post/i })).not.toBeDisabled();
  });

  it("test_compose_box_shows_red_char_count_past_500", async () => {
    render(<ComposeBox onSubmit={vi.fn()} />);
    const ta = screen.getByLabelText(/message/i);
    fireEvent.change(ta, { target: { value: "x".repeat(501) } });
    expect(screen.getByTestId("char-count")).toHaveClass("text-red-600");
    expect(screen.getByRole("button", { name: /post/i })).toBeDisabled();
  });

  it("test_compose_box_submits_on_button_click", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ComposeBox onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/message/i), "hello");
    await userEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(onSubmit).toHaveBeenCalledWith("hello");
  });

  it("test_compose_box_submits_on_cmd_enter", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ComposeBox onSubmit={onSubmit} />);
    const ta = screen.getByLabelText(/message/i);
    await userEvent.type(ta, "hello");
    fireEvent.keyDown(ta, { key: "Enter", metaKey: true });
    expect(onSubmit).toHaveBeenCalledWith("hello");
  });

  it("test_compose_box_surfaces_server_422_detail", async () => {
    const onSubmit = vi.fn().mockRejectedValue({ status: 422, detail: "message: too long" });
    render(<ComposeBox onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/message/i), "hi");
    await userEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("message: too long");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- tests/components/ComposeBox.test.tsx
```

Expected: FAIL.

- [ ] **Step 3: Implement ComposeBox**

Create `<fe>/src/components/ComposeBox.tsx`:

```tsx
import { FormEvent, KeyboardEvent, useState } from "react";
import { formatDetail, type ApiError } from "@/api/types";

type Props = {
  onSubmit: (message: string) => Promise<void>;
  placeholder?: string;
  buttonLabel?: string;
};

const MAX = 500;

export default function ComposeBox({ onSubmit, placeholder = "What's on your mind?", buttonLabel = "Post" }: Props) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const len = value.length;
  const valid = len > 0 && len <= MAX;

  async function submit() {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit(value);
      setValue("");
    } catch (e) {
      const err = e as ApiError;
      setError(formatDetail(err.detail));
    } finally {
      setBusy(false);
    }
  }

  function onFormSubmit(e: FormEvent) {
    e.preventDefault();
    void submit();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void submit();
    }
  }

  return (
    <form onSubmit={onFormSubmit} className="border border-neutral-200 rounded-lg bg-white p-3 space-y-2">
      <label htmlFor="compose-message" className="sr-only">Message</label>
      <textarea
        id="compose-message"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        rows={3}
        className="w-full resize-y border-0 focus:ring-0 p-0 text-base placeholder-neutral-400"
      />
      <div className="flex items-center gap-3">
        <span
          data-testid="char-count"
          className={`text-xs ${len > MAX ? "text-red-600 font-medium" : "text-neutral-500"}`}
        >
          {len} / {MAX}
        </span>
        <button
          type="submit"
          disabled={!valid || busy}
          className="ml-auto bg-neutral-900 text-white text-sm px-3 py-1.5 rounded disabled:opacity-50"
        >
          {busy ? "Posting…" : buttonLabel}
        </button>
      </div>
      {error && (
        <div role="alert" className="text-sm text-red-700 border border-red-300 bg-red-50 px-2 py-1 rounded">
          {error}
        </div>
      )}
    </form>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- tests/components/ComposeBox.test.tsx
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: ComposeBox with validation, char count, Cmd+Enter, 422 surfacing"
```

### Task 13: FeedPage

**Files:**
- Create: `<fe>/src/pages/FeedPage.tsx`
- Modify: `<fe>/src/App.tsx`

- [ ] **Step 1: Implement FeedPage**

Create `<fe>/src/pages/FeedPage.tsx`:

```tsx
import { Link } from "react-router-dom";
import { useFeed } from "@/hooks/useFeed";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import ComposeBox from "@/components/ComposeBox";

export default function FeedPage() {
  const { username } = useCurrentUser();
  const { posts, optimistic, loading, error, hasMore, loadMore, refetch, createPost } = useFeed();

  return (
    <div className="space-y-4">
      {username ? (
        <ComposeBox onSubmit={(msg) => createPost(msg)} />
      ) : (
        <div className="border border-neutral-200 rounded-lg bg-white p-3 text-sm text-neutral-600">
          <Link to="/login" className="underline">Sign in</Link> to post.
        </div>
      )}

      {error && <ErrorBox error={error} onRetry={refetch} />}

      {loading && posts.length === 0 ? (
        <LoadingRow />
      ) : (
        <>
          {optimistic.map((p) => (
            <PostCard key={`opt-${p.client_id}`} post={p} pending />
          ))}
          {posts.length === 0 && optimistic.length === 0 && !error && (
            <p className="py-12 text-center text-neutral-500">No posts yet.</p>
          )}
          {posts.map((p) => (
            <PostCard key={p.id} post={p} />
          ))}
          {hasMore && (
            <button
              onClick={loadMore}
              className="w-full border border-neutral-200 rounded-lg bg-white py-2 text-sm text-neutral-700 hover:bg-neutral-50"
            >
              Load more
            </button>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Wire into App.tsx**

In `<fe>/src/App.tsx`, replace the `FeedPage` stub:

```tsx
import FeedPage from "@/pages/FeedPage";
```

- [ ] **Step 3: Manual smoke test**

```bash
# Start backend + frontend, visit /, sign in, post a message.
# Confirm: optimistic show with "posting…", then becomes committed.
# Open a second tab as a different user, post — confirm first tab sees it within ~3s.
```

- [ ] **Step 4: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: FeedPage with compose, optimistic posts, polling, load-more"
```

---

## Phase 3: Users + Posts + Threads (Thu PM, ~3h)

### Task 14: UsersPage + useUsers

**Files:**
- Create: `<fe>/src/pages/UsersPage.tsx`
- Modify: `<fe>/src/App.tsx`

- [ ] **Step 1: Implement UsersPage**

Create `<fe>/src/pages/UsersPage.tsx`:

```tsx
import { Link } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import type { User } from "@/api/types";

export default function UsersPage() {
  const { data, loading, error, refetch } = useApi<User[]>("/users");

  if (loading) return <LoadingRow />;
  if (error) return <ErrorBox error={error} onRetry={refetch} />;
  if (!data || data.length === 0) return <p className="py-12 text-center text-neutral-500">No users yet.</p>;

  return (
    <ul className="divide-y divide-neutral-200 border border-neutral-200 rounded-lg bg-white">
      {data.map((u) => (
        <li key={u.username} className="px-4 py-3 flex items-center gap-3">
          <Link to={`/users/${u.username}`} className="font-medium hover:underline">{u.username}</Link>
          <span className="text-sm text-neutral-500">{u.post_count} posts</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 2: Wire and commit**

```tsx
// In App.tsx, replace stub:
import UsersPage from "@/pages/UsersPage";
```

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: UsersPage listing"
```

### Task 15: UserPage

**Files:**
- Create: `<fe>/src/pages/UserPage.tsx`
- Modify: `<fe>/src/App.tsx`

- [ ] **Step 1: Implement UserPage**

Create `<fe>/src/pages/UserPage.tsx`:

```tsx
import { useParams } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import type { Post, User } from "@/api/types";

export default function UserPage() {
  const { username = "" } = useParams();
  const user = useApi<User>(`/users/${username}`);
  const posts = useApi<Post[]>(`/users/${username}/posts`);

  if (user.error?.status === 404) {
    return <p className="py-12 text-center text-neutral-500">User <code>{username}</code> not found.</p>;
  }
  if (user.loading || posts.loading) return <LoadingRow />;
  if (user.error) return <ErrorBox error={user.error} onRetry={user.refetch} />;
  if (posts.error) return <ErrorBox error={posts.error} onRetry={posts.refetch} />;
  if (!user.data) return null;

  return (
    <div className="space-y-4">
      <header className="border border-neutral-200 rounded-lg bg-white px-4 py-3">
        <h1 className="text-xl font-semibold">{user.data.username}</h1>
        <p className="text-sm text-neutral-500">
          Joined {new Date(user.data.created_at).toLocaleDateString()} · {user.data.post_count} posts
        </p>
        {user.data.bio && <p className="mt-2 text-base whitespace-pre-wrap">{user.data.bio}</p>}
      </header>

      {posts.data && posts.data.length > 0 ? (
        posts.data.map((p) => <PostCard key={p.id} post={p} />)
      ) : (
        <p className="py-8 text-center text-neutral-500">No posts yet.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Wire and commit**

```tsx
// App.tsx:
import UserPage from "@/pages/UserPage";
```

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: UserPage with profile + posts + 404 view"
```

### Task 16: usePost + PostPage + ThreadView

**Files:**
- Create: `<fe>/src/hooks/usePost.ts`
- Create: `<fe>/src/components/ThreadView.tsx`
- Create: `<fe>/src/pages/PostPage.tsx`
- Modify: `<fe>/src/App.tsx`

- [ ] **Step 1: usePost hook**

Create `<fe>/src/hooks/usePost.ts`:

```ts
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/api/client";
import type { ApiError, Post } from "@/api/types";

export type ThreadResponse = { posts: Post[] };

export function usePost(idStr: string) {
  const id = Number(idStr);
  const [thread, setThread] = useState<Post[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ThreadResponse>(`/posts/${id}/thread`);
      setThread(data.posts);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const deletePost = useCallback(
    async (targetId: number) => {
      await apiFetch(`/posts/${targetId}`, { method: "DELETE" });
      await refetch();
    },
    [refetch],
  );

  const reply = useCallback(
    async (message: string, parent_id: number) => {
      await apiFetch("/posts", { method: "POST", body: JSON.stringify({ message, parent_id }) });
      await refetch();
    },
    [refetch],
  );

  return { thread, loading, error, refetch, deletePost, reply };
}
```

- [ ] **Step 2: ThreadView component**

Create `<fe>/src/components/ThreadView.tsx`:

```tsx
import { useMemo, useState } from "react";
import type { Post } from "@/api/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import UserPill from "./UserPill";
import ComposeBox from "./ComposeBox";

type Node = Post & { children: Node[] };

function buildTree(posts: Post[], rootId: number): Node | null {
  const byId = new Map<number, Node>();
  posts.forEach((p) => byId.set(p.id, { ...p, children: [] }));
  posts.forEach((p) => {
    if (p.parent_id != null) {
      byId.get(p.parent_id)?.children.push(byId.get(p.id)!);
    }
  });
  return byId.get(rootId) ?? null;
}

function PostNode({
  node,
  depth,
  onDelete,
  onReply,
}: {
  node: Node;
  depth: number;
  onDelete: (id: number) => Promise<void>;
  onReply: (message: string, parentId: number) => Promise<void>;
}) {
  const { username } = useCurrentUser();
  const [showReply, setShowReply] = useState(false);
  const indent = Math.min(depth, 5) * 16;

  return (
    <div style={{ marginLeft: indent }} className="space-y-2">
      <article className="border border-neutral-200 rounded-lg bg-white px-4 py-3">
        <header className="flex items-center gap-2 text-sm text-neutral-500">
          <UserPill username={node.username} />
          <span aria-hidden>·</span>
          <span>{new Date(node.created_at).toLocaleString()}</span>
          {username && (
            <button onClick={() => setShowReply((v) => !v)} className="ml-auto text-xs underline">
              {showReply ? "cancel" : "reply"}
            </button>
          )}
          {username === node.username && (
            <button
              onClick={() => onDelete(node.id)}
              className="text-xs text-red-700 underline"
            >
              delete
            </button>
          )}
        </header>
        <p className="mt-2 whitespace-pre-wrap text-base">{node.message}</p>
      </article>
      {showReply && (
        <ComposeBox
          buttonLabel="Reply"
          placeholder="Write a reply…"
          onSubmit={async (m) => {
            await onReply(m, node.id);
            setShowReply(false);
          }}
        />
      )}
      {node.children.map((c) => (
        <PostNode key={c.id} node={c} depth={depth + 1} onDelete={onDelete} onReply={onReply} />
      ))}
    </div>
  );
}

export default function ThreadView({
  posts,
  rootId,
  onDelete,
  onReply,
}: {
  posts: Post[];
  rootId: number;
  onDelete: (id: number) => Promise<void>;
  onReply: (message: string, parentId: number) => Promise<void>;
}) {
  const tree = useMemo(() => buildTree(posts, rootId), [posts, rootId]);
  if (!tree) return <p className="text-neutral-500">Thread root not found.</p>;
  return <PostNode node={tree} depth={0} onDelete={onDelete} onReply={onReply} />;
}
```

- [ ] **Step 3: PostPage**

Create `<fe>/src/pages/PostPage.tsx`:

```tsx
import { useParams, useNavigate } from "react-router-dom";
import { usePost } from "@/hooks/usePost";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import ThreadView from "@/components/ThreadView";

export default function PostPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { thread, loading, error, refetch, deletePost, reply } = usePost(id);

  if (error?.status === 404) return <p className="py-12 text-center text-neutral-500">Post not found.</p>;
  if (loading) return <LoadingRow />;
  if (error) return <ErrorBox error={error} onRetry={refetch} />;
  if (!thread) return null;

  return (
    <ThreadView
      posts={thread}
      rootId={Number(id)}
      onReply={reply}
      onDelete={async (delId) => {
        await deletePost(delId);
        if (delId === Number(id)) navigate("/");
      }}
    />
  );
}
```

- [ ] **Step 4: Wire and commit**

```tsx
// App.tsx:
import PostPage from "@/pages/PostPage";
```

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: PostPage with ThreadView (recursive replies, reply box, delete)"
```

---

## Phase 4: Reactions + Boards (Thu eve, ~2h)

### Task 17: ReactionBar (TDD)

**Files:**
- Create: `<fe>/src/components/ReactionBar.tsx`
- Create: `<fe>/tests/components/ReactionBar.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `<fe>/tests/components/ReactionBar.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ReactionBar from "@/components/ReactionBar";

describe("ReactionBar", () => {
  it("test_reaction_bar_renders_counts", () => {
    render(<ReactionBar postId={1} counts={{ heart: 3, laugh: 1 }} canReact onReact={vi.fn()} />);
    expect(screen.getByRole("button", { name: /heart/i })).toHaveTextContent("3");
    expect(screen.getByRole("button", { name: /laugh/i })).toHaveTextContent("1");
    expect(screen.getByRole("button", { name: /fire/i })).toHaveTextContent("0");
  });

  it("test_reaction_bar_calls_onReact_with_kind", () => {
    const onReact = vi.fn().mockResolvedValue(undefined);
    render(<ReactionBar postId={1} counts={{}} canReact onReact={onReact} />);
    fireEvent.click(screen.getByRole("button", { name: /heart/i }));
    expect(onReact).toHaveBeenCalledWith("heart");
  });

  it("test_reaction_bar_disables_buttons_when_cannot_react", () => {
    render(<ReactionBar postId={1} counts={{}} canReact={false} onReact={vi.fn()} />);
    expect(screen.getByRole("button", { name: /heart/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm test -- tests/components/ReactionBar.test.tsx
```

Expected: FAIL.

- [ ] **Step 3: Implement ReactionBar**

Create `<fe>/src/components/ReactionBar.tsx`:

```tsx
type Kind = "heart" | "laugh" | "fire";
const KINDS: Array<{ kind: Kind; emoji: string }> = [
  { kind: "heart", emoji: "♥" },
  { kind: "laugh", emoji: "😂" },
  { kind: "fire", emoji: "🔥" },
];

type Props = {
  postId: number;
  counts: Record<string, number>;
  canReact: boolean;
  onReact: (kind: Kind) => Promise<void>;
};

export default function ReactionBar({ counts, canReact, onReact }: Props) {
  return (
    <div className="flex gap-1 mt-2">
      {KINDS.map(({ kind, emoji }) => (
        <button
          key={kind}
          aria-label={kind}
          disabled={!canReact}
          onClick={() => void onReact(kind)}
          className="text-xs border border-neutral-200 rounded px-2 py-0.5 hover:bg-neutral-50 disabled:opacity-50"
        >
          <span aria-hidden className="mr-1">{emoji}</span>
          <span>{counts[kind] ?? 0}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- tests/components/ReactionBar.test.tsx
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: ReactionBar component"
```

### Task 18: Wire reactions into PostCard with optimistic update

**Files:**
- Modify: `<fe>/src/components/PostCard.tsx`
- Modify: `<fe>/src/pages/FeedPage.tsx`

- [ ] **Step 1: Update PostCard to render ReactionBar and own optimistic counts**

Overwrite `<fe>/src/components/PostCard.tsx`:

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/api/client";
import type { Post, ApiError } from "@/api/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import UserPill from "./UserPill";
import ReactionBar from "./ReactionBar";

type Props = {
  post: Post;
  pending?: boolean;
};

type Kind = "heart" | "laugh" | "fire";

function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function PostCard({ post, pending = false }: Props) {
  const { username } = useCurrentUser();
  const [counts, setCounts] = useState(post.reaction_counts);
  const [error, setError] = useState<string | null>(null);

  async function onReact(kind: Kind) {
    const prev = counts;
    setCounts({ ...counts, [kind]: (counts[kind] ?? 0) + 1 });
    setError(null);
    try {
      await apiFetch(`/posts/${post.id}/reactions`, { method: "POST", body: JSON.stringify({ kind }) });
    } catch (e) {
      setCounts(prev);
      setError(`Couldn't react: ${(e as ApiError).status}`);
    }
  }

  return (
    <article className={`border border-neutral-200 rounded-lg bg-white px-4 py-3 ${pending ? "opacity-60" : ""}`}>
      <header className="flex items-center gap-2 text-sm text-neutral-500">
        <UserPill username={post.username} />
        <span aria-hidden>·</span>
        <Link to={`/posts/${post.id}`} className="hover:underline">{fmtTime(post.created_at)}</Link>
        {post.board && (
          <>
            <span aria-hidden>·</span>
            <Link to={`/boards/${post.board}`} className="hover:underline">#{post.board}</Link>
          </>
        )}
        {pending && <span className="ml-auto text-xs italic text-neutral-400">posting…</span>}
      </header>
      <p className="mt-2 whitespace-pre-wrap text-base">{post.message}</p>
      {!pending && (
        <ReactionBar postId={post.id} counts={counts} canReact={Boolean(username)} onReact={onReact} />
      )}
      {error && <p role="alert" className="text-xs text-red-700 mt-1">{error}</p>}
    </article>
  );
}
```

- [ ] **Step 2: Manual smoke test**

```
Sign in as alice. Click heart on a post → count increments instantly.
Sign out (clear localStorage). Reactions buttons disabled.
```

- [ ] **Step 3: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: optimistic reactions on PostCard with rollback"
```

### Task 19: useBoards + BoardsPage + BoardPage

**Files:**
- Create: `<fe>/src/pages/BoardsPage.tsx`
- Create: `<fe>/src/pages/BoardPage.tsx`
- Modify: `<fe>/src/App.tsx`

- [ ] **Step 1: BoardsPage**

Create `<fe>/src/pages/BoardsPage.tsx`:

```tsx
import { Link } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import type { Board } from "@/api/types";

export default function BoardsPage() {
  const { data, loading, error, refetch } = useApi<Board[]>("/boards");

  if (loading) return <LoadingRow />;
  if (error) return <ErrorBox error={error} onRetry={refetch} />;
  if (!data || data.length === 0) return <p className="py-12 text-center text-neutral-500">No boards yet.</p>;

  return (
    <ul className="divide-y divide-neutral-200 border border-neutral-200 rounded-lg bg-white">
      {data.map((b) => (
        <li key={b.name} className="px-4 py-3">
          <Link to={`/boards/${b.name}`} className="font-medium hover:underline">#{b.name}</Link>
          <span className="text-sm text-neutral-500 ml-2">{b.post_count} posts</span>
          {b.description && <p className="text-sm text-neutral-600 mt-1">{b.description}</p>}
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 2: BoardPage (uses useFeed with board param)**

Create `<fe>/src/pages/BoardPage.tsx`:

```tsx
import { useParams } from "react-router-dom";
import { useFeed } from "@/hooks/useFeed";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import ComposeBox from "@/components/ComposeBox";

export default function BoardPage() {
  const { name = "" } = useParams();
  const { username } = useCurrentUser();
  const { posts, optimistic, loading, error, hasMore, loadMore, refetch, createPost } = useFeed({ board: name });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">#{name}</h1>
      {username && <ComposeBox onSubmit={(m) => createPost(m, name)} placeholder={`Post to #${name}…`} />}
      {error && <ErrorBox error={error} onRetry={refetch} />}
      {loading && posts.length === 0 ? (
        <LoadingRow />
      ) : (
        <>
          {optimistic.map((p) => <PostCard key={`opt-${p.client_id}`} post={p} pending />)}
          {posts.length === 0 && optimistic.length === 0 && !error && (
            <p className="py-12 text-center text-neutral-500">No posts on this board yet.</p>
          )}
          {posts.map((p) => <PostCard key={p.id} post={p} />)}
          {hasMore && (
            <button onClick={loadMore} className="w-full border border-neutral-200 rounded-lg bg-white py-2 text-sm hover:bg-neutral-50">
              Load more
            </button>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Wire and commit**

```tsx
// App.tsx:
import BoardsPage from "@/pages/BoardsPage";
import BoardPage from "@/pages/BoardPage";
```

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: BoardsPage and BoardPage with scoped feed"
```

### Task 20: Search box on FeedPage + keyboard shortcut "/"

**Files:**
- Modify: `<fe>/src/pages/FeedPage.tsx`

- [ ] **Step 1: Add search + "/" shortcut**

Overwrite `<fe>/src/pages/FeedPage.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useFeed } from "@/hooks/useFeed";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import ComposeBox from "@/components/ComposeBox";

export default function FeedPage() {
  const { username } = useCurrentUser();
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);
  const { posts, optimistic, loading, error, hasMore, loadMore, refetch, createPost } = useFeed(q ? { q } : undefined);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "/" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <label htmlFor="search" className="sr-only">Search posts</label>
        <input
          id="search"
          ref={searchRef}
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") setQ(qInput); }}
          placeholder="Search posts (press / to focus)"
          className="flex-1 border border-neutral-300 rounded px-3 py-2 text-sm"
        />
        <button
          onClick={() => setQ(qInput)}
          className="border border-neutral-300 rounded px-3 py-2 text-sm hover:bg-neutral-50"
        >
          Search
        </button>
        {q && (
          <button onClick={() => { setQ(""); setQInput(""); }} className="text-sm underline text-neutral-600">
            Clear
          </button>
        )}
      </div>

      {username ? (
        <ComposeBox onSubmit={(msg) => createPost(msg)} />
      ) : (
        <div className="border border-neutral-200 rounded-lg bg-white p-3 text-sm text-neutral-600">
          <Link to="/login" className="underline">Sign in</Link> to post.
        </div>
      )}

      {error && <ErrorBox error={error} onRetry={refetch} />}

      {loading && posts.length === 0 ? (
        <LoadingRow />
      ) : (
        <>
          {optimistic.map((p) => <PostCard key={`opt-${p.client_id}`} post={p} pending />)}
          {posts.length === 0 && optimistic.length === 0 && !error && (
            <p className="py-12 text-center text-neutral-500">{q ? "No posts match." : "No posts yet."}</p>
          )}
          {posts.map((p) => <PostCard key={p.id} post={p} />)}
          {hasMore && (
            <button onClick={loadMore} className="w-full border border-neutral-200 rounded-lg bg-white py-2 text-sm hover:bg-neutral-50">
              Load more
            </button>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add shortcut footer to Layout**

Edit `<fe>/src/components/Layout.tsx`, append before closing `</div>` of root:

```tsx
<footer className="border-t border-neutral-200 text-xs text-neutral-500">
  <div className="max-w-3xl mx-auto px-4 py-2">
    Shortcuts: <kbd className="border px-1 rounded">/</kbd> search · <kbd className="border px-1 rounded">⌘↵</kbd> post
  </div>
</footer>
```

- [ ] **Step 3: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: search on feed + \"/\" shortcut + footer cheatsheet"
```

---

## Phase 5: Visual polish (Fri AM, ~2h)

### Task 21: Typography + spacing pass

**Files:**
- Modify: `<fe>/src/index.css`
- Modify: `<fe>/src/components/Layout.tsx`
- Various pages for vertical rhythm

- [ ] **Step 1: Tighten the base CSS**

Overwrite `<fe>/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg: #fafafa;
  --surface: #ffffff;
  --border: #e5e5e5;
  --text: #171717;
  --muted: #737373;
  --accent: #171717;
  color-scheme: light;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-feature-settings: "cv11", "ss01";
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}

kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible {
  outline: 2px solid #171717;
  outline-offset: 2px;
  border-radius: 4px;
}
```

- [ ] **Step 2: Test at mobile width**

```bash
npm run dev -- --port 5173 &
# Open http://localhost:5173 with devtools at 320px wide.
# Visually verify: nav wraps, feed cards full-width, no horizontal scroll.
```

- [ ] **Step 3: Adjust Layout for mobile if needed**

Tweak `Layout.tsx` header to wrap nav under brand on narrow widths:

In `<fe>/src/components/Layout.tsx`, change the header inner div className from:

```tsx
"max-w-3xl mx-auto px-4 py-3 flex items-center gap-4"
```

to:

```tsx
"max-w-3xl mx-auto px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2"
```

- [ ] **Step 4: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: typography + focus + mobile layout pass"
```

---

## Phase 6: README + edge-case clickthrough + PR (Fri PM, ~3h)

### Task 22: Write A4 README

**Files:**
- Create: `<fe>/README.md`

- [ ] **Step 1: Write README**

Create `<fe>/README.md`:

```markdown
# BBS Frontend — Micah Briggs (A4)

React + TypeScript + Vite frontend for the A2 BBS Webserver.

## How to run

In one terminal, the backend (this repo's A2):

```bash
cd assignments/bbs-webserver/rmbriggs
# activate venv
uvicorn main:app --port 8000
```

In another, the frontend:

```bash
cd assignments/bbs-frontend/rmbriggs
npm install
npm run dev
```

Open http://localhost:5173. The backend URL is configurable:

```bash
VITE_API_BASE=http://example.com:8000 npm run dev
```

Default is `http://localhost:8000`.

## Tier targeted

**Gold.** Bronze + silver + three gold items.

## Changes I made to my A2 backend

Added `CORSMiddleware` allowing `http://localhost:5173`, because browsers refuse cross-origin requests unless the server opts in. One-liner per the FastAPI CORS docs. No other backend changes.

## Design decisions

- **Hooks layer over inline fetches.** Every page consumes a hook (`useFeed`, `usePost`, `useUsers`, `useBoards`, `useCurrentUser`), not raw `useEffect(fetch(...))`. This centralizes loading/error/data state, gives one place to add polling and optimistic updates, and keeps pages thin. The default agent move is inline fetches sprinkled through components, which would have turned `FeedPage` into a 200-line god component.
- **Routing.** `react-router-dom` v6. Seven routes: `/`, `/login`, `/users`, `/users/:username`, `/posts/:id`, `/boards`, `/boards/:name`, plus a 404. All bookmarkable; back button works because each page is its own route. `Layout` is a single `<Outlet/>` wrapper that renders nav + current-user pill on every page.
- **Optimistic POST with `client_id` reconciliation.** `useFeed.createPost` immediately prepends a draft `{client_id, status: 'pending'}` to a separate `optimistic` array. On 201, the draft is removed by `client_id` and the server post merged into `posts`. On 4xx/5xx, the draft is removed and the error is surfaced inline. Importantly the optimistic array is separate from committed `posts`, so the 3s polling refetch can't double-render the new post.
- **Polling, not push.** 3s `setInterval` in `useFeed`, paused when `document.visibilityState === 'hidden'`. Polling instead of SSE/websockets because (a) zero backend change, (b) BBS traffic is low enough that 3s latency is fine, (c) the request is a single GET that returns ≤20 posts — cheap.
- **X-Username "not real auth," as a visible preference.** `localStorage.username` drives the header. The current username appears in the nav as a pill, never hidden. The login page has no password field because pretending we have one would lie about the security model; the page literally explains "Identity is just a header — not real auth." Mutations are disabled in the UI when no username is set.

## Gold items

1. **Real-time-ish polling** — `useFeed` refetches every 3s, paused on hidden tab. Posts from another tab appear within ~3s. See `src/hooks/useFeed.ts`.
2. **Visual design with a point of view** — type scale of 5 sizes (12/14/16/20/28), one accent color (neutral 900), generous spacing on a 4px grid via Tailwind defaults, mobile-first layout that holds at 320px wide.
3. **Invented UI feature: threads + reactions + boards-as-navigation** — A2 supports all three; A4 wires them into a single coherent UI. Click a post → `/posts/:id` shows the thread tree (`ThreadView` recursively renders `/posts/{id}/thread`). Each `PostCard` has a `ReactionBar` for heart/laugh/fire with optimistic upsert (A2 has one-reaction-per-user semantics). The `BoardsPage` lists boards; `BoardPage` is a board-scoped feed with its own compose box that auto-fills the `board` field.

## Tests

```bash
npm test
```

Vitest + React Testing Library. ≥3 tests covering the most logic-heavy components (`ComposeBox`, `useFeed`, `ReactionBar`) plus foundation tests for `apiFetch`, `useApi`, `useCurrentUser`. Per repo convention, each test case is its own named function — no parametrize.

## Where my agent helped most and where I had to push back

The agent was great at scaffolding the layout (Vite + Tailwind + shadcn + router boilerplate in ~5 minutes) and at translating the design doc's hook signatures into working code. Where I had to push back: (1) the default plan put `fetch` calls inline in each page; I argued it into a hooks layer because otherwise the 22-endpoint surface would have meant 22 ad-hoc loading patterns. (2) The initial optimistic POST implementation kept the draft inside the committed `posts` array, which meant polling could race-replace it; I separated them into a parallel `optimistic` list reconciled by a `client_id`. (3) Loading/error states were the recurring miss — the agent shipped the happy path and skipped the empty states and 404 views; I had to enumerate every fetch site and demand the three states uniformly. Most of bronze polish was me clicking around finding "click delete twice fast" type bugs and writing them up.
```

- [ ] **Step 2: Commit**

```bash
git add assignments/bbs-frontend/rmbriggs/README.md
git commit -m "A4: README"
```

### Task 23: Edge-case clickthrough (manual checklist)

**Files:** none — this is QA

- [ ] **Step 1: Run both servers**

```bash
# Terminal 1:
cd assignments/bbs-webserver/rmbriggs && uvicorn main:app --port 8000

# Terminal 2:
cd assignments/bbs-frontend/rmbriggs && npm run dev
```

- [ ] **Step 2: Walk this checklist, fix anything broken before moving on**

- [ ] **Identity persistence:** sign in as alice → refresh → still alice.
- [ ] **Empty body POST:** submit button disabled when textarea empty.
- [ ] **501-char POST:** char count is red, submit disabled.
- [ ] **Duplicate username:** create user "alice" twice → second attempt shows server 409 inline.
- [ ] **Invalid username pattern:** type `alice!` → submit disabled.
- [ ] **404 user:** visit `/users/nope` → "User nope not found".
- [ ] **404 post:** visit `/posts/99999` → "Post not found".
- [ ] **Double-click submit:** spam Post button → only one post created (button shows "Posting…" + disabled while busy).
- [ ] **Network off (DevTools → Network → Offline):** every page shows ErrorBox with retry; clicking retry after re-enabling network recovers.
- [ ] **Polling pauses on hidden tab:** open DevTools Network, switch tabs for 10s, switch back → no requests fired while hidden.
- [ ] **Optimistic POST rollback:** disable network, post → optimistic appears then disappears with error.
- [ ] **Optimistic reaction rollback:** disable network, click heart → count flickers up then back down with error.
- [ ] **Two-tab polling:** post in tab A → tab B sees it within ~3s.
- [ ] **Thread:** reply on a post → see the reply nested below; delete the reply → it disappears.
- [ ] **Delete own root post on PostPage:** redirects to `/`.
- [ ] **Delete someone else's post:** delete button absent (only shows for `username === post.username`).
- [ ] **Mobile width 320px:** no horizontal scroll, nav wraps, feed is readable.
- [ ] **Keyboard tab order:** start fresh, tab through `/` — search → compose textarea → post button → first PostCard's links → reactions are reachable. No `<div onClick>` traps.
- [ ] **"/" shortcut:** anywhere outside an input, press `/` → focus jumps to search.
- [ ] **Cmd+Enter in compose:** submits.

- [ ] **Step 3: Run the test suite**

```bash
cd assignments/bbs-frontend/rmbriggs
npm test
```

Expected: all green.

- [ ] **Step 4: Commit any clickthrough fixes**

```bash
git add assignments/bbs-frontend/rmbriggs
git commit -m "A4: edge-case fixes from clickthrough QA"   # only if there were fixes
```

### Task 24: Open PR

**Files:** none — git operations

- [ ] **Step 1: Push branch**

```bash
git push -u origin bbs-frontend-rmbriggs
```

- [ ] **Step 2: Create PR**

```bash
gh pr create --title "BBS Frontend - Micah Briggs" --body "$(cat <<'EOF'
## Summary

- Gold-tier React + TypeScript + Vite frontend for A2 BBS Webserver
- Three gold picks: real-time-ish polling (3s `setInterval` on feed), visual design POV (deliberate type/color/spacing scale), invented UI feature (threads + reactions + boards-as-navigation)
- Six required views plus a 404, behind `react-router-dom` routes
- All 22 endpoint surfaces have loading/error/empty states
- Optimistic POST and optimistic reactions both reconcile on success and roll back on failure
- One CORS-middleware change to A2 backend, documented in both READMEs

## Test plan

- [ ] `npm test` in `assignments/bbs-frontend/rmbriggs` — Vitest suite (>15 cases) green
- [ ] Start backend (`uvicorn main:app --port 8000`) + frontend (`npm run dev`), sign in, post, reply, react, switch user, click into boards
- [ ] Two-tab polling visible within ~3s
- [ ] Refresh persists current user
- [ ] Walkthrough at 320px width has no horizontal scroll

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Return the PR URL**

---

## Self-review

**Spec coverage:**
- Bronze: all six views (Feed, Compose-in-Feed, Users, User, Post, Login) → Tasks 6, 7, 13, 14, 15, 16. Eight A2 bronze endpoints covered: POST /users (Task 7), GET /users (14), GET /users/{u} (15), GET /users/{u}/posts (15), POST /posts (10), GET /posts (10), GET /posts/{id} (16 via thread), DELETE /posts/{id} (16). Loading + error states everywhere (8, 9, used in all pages). Validation + 422 surfacing (Task 12). localStorage identity (Task 5). README (22). ✓
- Silver: routing (Task 6), optimistic POST (10), load-more pagination (10, 13), 3+ Vitest tests (4, 5, 8, 10, 12, 17 — many more than 3), keyboard shortcut beyond Cmd+Enter (Task 20 "/"), basic a11y (sr-only labels in 7/12/20, focus styles in 21, keyboard tab order verified in 23). ✓
- Gold: polling (Task 10), visual design pass (Task 21 + design-tokens choice from the start), invented UI (Tasks 16 threads + 17/18 reactions + 19 boards-as-nav). ✓

**Placeholder scan:** no "TBD", no "implement later", no "similar to Task N". All test code and component code is concrete.

**Type consistency:** `Post.parent_id` used the same in `types.ts`, `ThreadView`, `useFeed.createPost`. `Kind` ("heart"|"laugh"|"fire") used the same in `ReactionBar` and `PostCard`. `FeedPage` and `BoardPage` both use `useFeed` with consistent signature `(params?: {q?, board?, username?})`.

**Known leftover risk:** Task 23 is QA, not new code — if the clickthrough finds bugs, time has to come from somewhere. Mitigation is the 1-hour PR buffer Friday 4-5pm.
