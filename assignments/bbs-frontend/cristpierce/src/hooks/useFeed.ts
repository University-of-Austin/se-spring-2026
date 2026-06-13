/*
 * useFeed — the home feed's data layer. This is where the app's interesting
 * state lives, so it is deliberately its own unit.
 *
 * Reads:   GET /posts?q=&limit=&offset=  (offset pagination, "load more")
 * Live:    GET /feed?since=<newest>      (polled every 5s, delta only)
 * Writes:  optimistic prepend / replace / remove / restore helpers that the
 *          Composer and PostCard call so the UI reacts instantly and rolls
 *          back on failure.
 *
 * Design choices worth narrating:
 *  - Polling only runs on the UNFILTERED feed, on the first page, while the tab
 *    is visible. A search result set isn't a live stream, and polling a
 *    hidden tab wastes requests.
 *  - New live posts are NOT auto-injected (that would yank scroll position).
 *    They are stashed in `pending` and surfaced as a "N new posts" pill the
 *    user clicks to merge — the standard social-feed pattern.
 *  - Every merge dedups by post id, so an optimistic post, its server echo,
 *    and a later poll of the same row never produce duplicates.
 */

import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { api } from '../lib/api'
import type { Post } from '../lib/types'
import { toApiError, type Status } from './useResource'
import type { ApiError } from '../lib/api'

export const PAGE_SIZE = 20
const POLL_INTERVAL_MS = 5_000

type FeedAction =
  | { type: 'set'; posts: Post[] }
  | { type: 'append'; posts: Post[] }
  | { type: 'prepend'; posts: Post[] }
  | { type: 'replace'; tempId: number; post: Post }
  | { type: 'remove'; id: number }
  | { type: 'restore'; post: Post }

function dedupAgainst(existing: Post[], incoming: Post[]): Post[] {
  const seen = new Set(existing.map((p) => p.id))
  return incoming.filter((p) => !seen.has(p.id))
}

function feedReducer(state: Post[], action: FeedAction): Post[] {
  switch (action.type) {
    case 'set':
      return action.posts
    case 'append':
      return [...state, ...dedupAgainst(state, action.posts)]
    case 'prepend':
      return [...dedupAgainst(state, action.posts), ...state]
    case 'replace': {
      // If the placeholder is gone (a concurrent reload/search replaced the
      // list while the POST was in flight), still surface the confirmed post
      // instead of silently dropping it.
      if (!state.some((p) => p.id === action.tempId)) {
        return [...dedupAgainst(state, [action.post]), ...state]
      }
      return state.map((p) => (p.id === action.tempId ? action.post : p))
    }
    case 'remove':
      return state.filter((p) => p.id !== action.id)
    case 'restore': {
      if (state.some((p) => p.id === action.post.id)) return state
      const next = [...state, action.post]
      next.sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id)
      return next
    }
    default:
      return state
  }
}

function newestCreatedAt(...lists: Post[][]): string | undefined {
  let newest: string | undefined
  for (const list of lists) {
    for (const p of list) {
      // Skip optimistic (negative-id) posts: their placeholder timestamp isn't
      // a server timestamp and must not become the polling cursor.
      if (p.id < 0) continue
      if (!newest || p.created_at > newest) newest = p.created_at
    }
  }
  return newest
}

export interface FeedController {
  items: Post[]
  status: Status
  error: ApiError | undefined
  hasMore: boolean
  loadingMore: boolean
  loadMore: () => Promise<void>
  refresh: () => void
  /** Live posts discovered by polling but not yet shown. */
  pendingCount: number
  showPending: () => void
  // Optimistic helpers (return values let callers roll back precisely):
  addOptimistic: (post: Post) => void
  replaceOptimistic: (tempId: number, post: Post) => void
  removeOptimistic: (id: number) => void
  restorePost: (post: Post) => void
}

export function useFeed(query: string): FeedController {
  const [items, dispatch] = useReducer(feedReducer, [])
  const [status, setStatus] = useState<Status>('loading')
  const [error, setError] = useState<ApiError | undefined>(undefined)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [pending, setPending] = useState<Post[]>([])
  const [nonce, setNonce] = useState(0)

  const offsetRef = useRef(0)
  const itemsRef = useRef<Post[]>(items)
  const pendingRef = useRef<Post[]>(pending)

  // Keep refs the polling interval reads in sync with the latest state.
  useEffect(() => {
    itemsRef.current = items
    pendingRef.current = pending
  }, [items, pending])

  // Initial load + reload on query change / manual refresh.
  useEffect(() => {
    let active = true
    const controller = new AbortController()
    setStatus('loading')
    setError(undefined)
    setPending([])
    offsetRef.current = 0

    api
      .listPosts({ q: query || undefined, limit: PAGE_SIZE, offset: 0 }, controller.signal)
      .then((posts) => {
        if (!active) return
        dispatch({ type: 'set', posts })
        offsetRef.current = posts.length
        setHasMore(posts.length === PAGE_SIZE)
        setStatus('success')
      })
      .catch((err: unknown) => {
        if (!active || controller.signal.aborted) return
        if (err instanceof DOMException && err.name === 'AbortError') return
        setError(toApiError(err))
        setStatus('error')
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [query, nonce])

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const posts = await api.listPosts({
        q: query || undefined,
        limit: PAGE_SIZE,
        offset: offsetRef.current,
      })
      dispatch({ type: 'append', posts })
      offsetRef.current += posts.length
      setHasMore(posts.length === PAGE_SIZE)
    } finally {
      setLoadingMore(false)
    }
  }, [query, hasMore, loadingMore])

  const refresh = useCallback(() => setNonce((n) => n + 1), [])

  // Live polling — delta fetch of posts newer than the newest we know about.
  useEffect(() => {
    if (query) return // don't poll a filtered/search view
    let cancelled = false

    const tick = async () => {
      if (document.visibilityState !== 'visible') return
      const since = newestCreatedAt(itemsRef.current, pendingRef.current)
      try {
        const fresh = await api.feedSince(since, 50)
        if (cancelled || fresh.length === 0) return
        const novel = dedupAgainst([...itemsRef.current, ...pendingRef.current], fresh)
        if (novel.length) {
          setPending((prev) => [...dedupAgainst(prev, novel), ...prev])
        }
      } catch {
        // Polling failures are non-fatal and self-healing; stay quiet rather
        // than flashing an error over a feed that's still perfectly readable.
      }
    }

    const interval = setInterval(tick, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [query])

  const showPending = useCallback(() => {
    setPending((p) => {
      if (p.length) {
        dispatch({ type: 'prepend', posts: p })
        // These are server rows now at the head of the list; advance the offset
        // cursor so the next "Load more" page stays aligned with the server.
        offsetRef.current += p.length
      }
      return []
    })
  }, [])

  const addOptimistic = useCallback((post: Post) => {
    dispatch({ type: 'prepend', posts: [post] })
  }, [])

  const replaceOptimistic = useCallback((tempId: number, post: Post) => {
    dispatch({ type: 'replace', tempId, post })
  }, [])

  const removeOptimistic = useCallback((id: number) => {
    dispatch({ type: 'remove', id })
  }, [])

  const restorePost = useCallback((post: Post) => {
    dispatch({ type: 'restore', post })
  }, [])

  return {
    items,
    status,
    error,
    hasMore,
    loadingMore,
    loadMore,
    refresh,
    pendingCount: pending.length,
    showPending,
    addOptimistic,
    replaceOptimistic,
    removeOptimistic,
    restorePost,
  }
}
