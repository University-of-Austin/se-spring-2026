// The feed: ComposeForm + SearchBar + scrolling post list with infinite scroll.
// Search is debounced 300ms — typing fast doesn't fire a request per keystroke.

import { useState, useEffect, useRef } from 'react'
import { usePosts } from '../hooks/usePosts'
import { useCurrentUser } from '../context/useCurrentUser'
import { PostCard } from '../components/PostCard'
import { Spinner } from '../components/Spinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { ComposeForm } from '../components/ComposeForm'
import { SearchBar } from '../components/SearchBar'

const LIMIT = 20
// How tall the scrolling post list is. Roughly 3 PostCard heights.
const FEED_MAX_HEIGHT_PX = 340
// Trigger next-page fetch when sentinel is within this many pixels of the
// scroll container's bottom edge.
const PREFETCH_DISTANCE_PX = 100
// How long to wait after the last keystroke before firing a search query.
const SEARCH_DEBOUNCE_MS = 300

export default function FeedPage() {
  const [offset, setOffset] = useState(0)
  // Immediate value bound to the input. Updates on every keystroke.
  const [searchInput, setSearchInput] = useState('')
  // Delayed value passed to the API. Catches up to searchInput after 300ms idle.
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const { posts, loading, error, lastFetchSize, refetch, addOptimistic, removeOptimistic } = usePosts({
    q: debouncedSearch || undefined,
    limit: LIMIT,
    offset,
  })
  const { username } = useCurrentUser()

  const postListRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  // Search input ref — focused when the user presses `/`.
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Debounce the search input → debouncedSearch. Each keystroke schedules
  // a new timer; the cleanup cancels the previous one. Only after 300ms of
  // no typing does debouncedSearch update and trigger a new fetch.
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [searchInput])

  // `/` focuses the search input (when not already typing somewhere).
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key !== '/') return
      const target = e.target
      if (target instanceof HTMLElement) {
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
          return
        }
      }
      e.preventDefault()
      searchInputRef.current?.focus()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [])

  // Poll for new posts when signed out, no search active, on first page.
  // Signed-in users already get optimistic updates from their own composes,
  // so polling there would mostly be redundant.
  useEffect(() => {
    if (username) return
    if (debouncedSearch) return
    if (offset !== 0) return
    const id = setInterval(() => refetch(), 3000)
    return () => clearInterval(id)
  }, [username, debouncedSearch, offset, refetch])

  // Reset pagination on any search change so the next fetch starts at offset 0.
  // (If we didn't, mid-pagination + new search would APPEND results to existing.)
  const handleSearchChange = (v: string) => {
    setSearchInput(v)
    setOffset(0)
  }

  const handlePosted = () => {
    if (offset === 0) refetch()
    else setOffset(0)
  }

  const hasMore = lastFetchSize === null || lastFetchSize === LIMIT
  const initialLoading = loading && posts.length === 0
  const loadingMore = loading && posts.length > 0

  // IntersectionObserver for infinite scroll within the post-list container.
  useEffect(() => {
    if (!hasMore || loading) return
    const sentinel = sentinelRef.current
    const root = postListRef.current
    if (!sentinel || !root) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setOffset(o => o + LIMIT)
        }
      },
      { root, rootMargin: `0px 0px ${PREFETCH_DISTANCE_PX}px 0px` }
    )

    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasMore, loading])

  return (
    <div className="space-y-6">
      {username && (
        <ComposeForm
          onPosted={handlePosted}
          addOptimistic={addOptimistic}
          removeOptimistic={removeOptimistic}
        />
      )}

      <SearchBar value={searchInput} onChange={handleSearchChange} ref={searchInputRef} />

      {initialLoading && <Spinner />}
      {error && <ErrorMessage error={error} />}

      {!initialLoading && !error && (
        posts.length === 0
          ? (
              debouncedSearch
                ? <p className="text-muted">No posts match "{debouncedSearch}".</p>
                : <p className="text-muted">No posts yet.</p>
            )
          : (
            <div
              ref={postListRef}
              style={{ maxHeight: `${FEED_MAX_HEIGHT_PX}px` }}
              className="space-y-3 overflow-y-auto scrollbar-hide"
              aria-live="polite"
            >
              {posts.map(post => <PostCard key={post.id} post={post} />)}

              {hasMore && (
                <div ref={sentinelRef} className="h-px" aria-hidden="true" />
              )}

              {loadingMore && (
                <p className="text-center text-muted text-sm py-2">Loading more…</p>
              )}

              {!hasMore && posts.length >= LIMIT && (
                <p className="text-center text-muted text-sm py-2">— end of feed —</p>
              )}
            </div>
          )
      )}
    </div>
  )
}
