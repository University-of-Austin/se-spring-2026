import { QueryClient } from '@tanstack/react-query'

/**
 * Defaults are tuned for the BBS shape:
 * - staleTime 30s — feed re-fetches don't fire on every navigation
 * - refetchOnWindowFocus on — recover after tab-back
 * - retry 1 — one retry is enough for hiccups; more masks real outages
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: 0,
    },
  },
})
