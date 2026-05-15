// In-memory router for bronze.
//
// The URL doesn't change as you navigate — that's an explicit silver
// requirement and would need react-router-dom or similar to do well.
// What this file provides is the *shape* an app needs from a router:
//
//   const { route, navigate } = useRouter();
//
// Views read `route` (a tagged union — `route.view` is one of the
// known view names, and `params` is narrowed by TypeScript) and call
// `navigate(...)` to change it.  When we go to silver, this entire
// file is replaced by a thin wrapper over react-router-dom's
// useNavigate + useParams.  View components stay unchanged.

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Route =
  | { view: "feed" }
  | { view: "compose" }
  | { view: "users" }
  | { view: "user"; username: string }
  | { view: "post"; id: number }
  | { view: "identity" };

type RouterContextValue = {
  route: Route;
  navigate: (route: Route) => void;
};

const RouterContext = createContext<RouterContextValue | null>(null);

export function RouterProvider({ children }: { children: ReactNode }) {
  const [route, setRoute] = useState<Route>({ view: "feed" });

  // Scroll to top on navigate.  Otherwise the user clicks a post on
  // page 5 of the feed, lands on detail, hits back, and is staring
  // at empty space because the post detail page was short.
  const navigate = useCallback((next: Route) => {
    setRoute(next);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, []);

  const value = useMemo<RouterContextValue>(() => ({ route, navigate }), [route, navigate]);

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter(): RouterContextValue {
  const ctx = useContext(RouterContext);
  if (!ctx) throw new Error("useRouter must be used inside <RouterProvider>");
  return ctx;
}
