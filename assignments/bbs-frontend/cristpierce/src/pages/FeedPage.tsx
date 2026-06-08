import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../lib/api'
import type { Post } from '../lib/types'
import { localIsoNow } from '../lib/time'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import { useFeed } from '../hooks/useFeed'
import { Composer } from '../components/Composer'
import { PostList } from '../components/PostList'
import { NewPostsPill } from '../components/NewPostsPill'
import { Button } from '../components/ui/Button'
import { EmptyState, ErrorView } from '../components/ui/StateView'
import { PostCardSkeleton } from '../components/ui/Skeleton'
import { CloseIcon, SearchIcon } from '../components/ui/icons'
import styles from './FeedPage.module.css'

export function FeedPage() {
  const { username } = useIdentity()
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const query = searchParams.get('q') ?? ''
  const [draft, setDraft] = useState(query)
  const feed = useFeed(query)
  const tempIdRef = useRef(-1)

  // Keep the input in sync when the URL query changes (e.g. browser back).
  useEffect(() => {
    setDraft(query)
  }, [query])

  // Debounce the search box into the URL so searches are shareable + survive
  // refresh, and the feed refetches off a stable, bookmarkable param.
  useEffect(() => {
    const trimmed = draft.trim()
    if (trimmed === query) return
    const id = setTimeout(() => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (trimmed) next.set('q', trimmed)
          else next.delete('q')
          return next
        },
        { replace: true },
      )
    }, 300)
    return () => clearTimeout(id)
  }, [draft, query, setSearchParams])

  async function handlePost(message: string) {
    if (!username) throw new ApiError({ status: 0, message: 'Choose a username first.' })
    const tempId = tempIdRef.current--
    const optimistic: Post = {
      id: tempId,
      username,
      message,
      created_at: localIsoNow(),
      updated_at: null,
    }
    feed.addOptimistic(optimistic)
    try {
      const real = await api.createPost(username, message)
      feed.replaceOptimistic(tempId, real)
      toast.success('Posted.')
    } catch (err) {
      feed.removeOptimistic(tempId)
      throw err // Composer surfaces the message inline
    }
  }

  async function handleDelete(post: Post) {
    feed.removeOptimistic(post.id)
    try {
      await api.deletePost(post.id)
    } catch (err) {
      feed.restorePost(post)
      toast.error(err instanceof ApiError ? err.message : 'Could not delete the post.')
    }
  }

  function handleUpdated(updated: Post) {
    feed.replaceOptimistic(updated.id, updated)
  }

  const searching = query.length > 0
  const showInitialLoading = feed.status === 'loading' && feed.items.length === 0
  const showInitialError = feed.status === 'error' && feed.items.length === 0
  const showEmpty = feed.status === 'success' && feed.items.length === 0

  return (
    <div className={styles.page}>
      <Composer onPost={handlePost} />

      <div className={styles.searchBox}>
        <SearchIcon size={16} className={styles.searchIcon} />
        <label htmlFor="feed-search" className="visually-hidden">
          Search posts
        </label>
        <input
          id="feed-search"
          type="search"
          className={styles.search}
          placeholder="Search posts…  ( press / )"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        {draft && (
          <button
            type="button"
            className={styles.clear}
            aria-label="Clear search"
            onClick={() => setDraft('')}
          >
            <CloseIcon size={15} />
          </button>
        )}
      </div>

      <NewPostsPill count={feed.pendingCount} onClick={feed.showPending} />

      {showInitialLoading ? (
        <div className={styles.skeletons}>
          <PostCardSkeleton />
          <PostCardSkeleton />
          <PostCardSkeleton />
        </div>
      ) : showInitialError ? (
        <ErrorView error={feed.error} onRetry={feed.refresh} title="Couldn’t load the feed" />
      ) : showEmpty ? (
        <EmptyState
          title={searching ? `No posts match “${query}”` : 'No posts yet'}
          hint={searching ? 'Try a different search term.' : 'Be the first to post something.'}
        />
      ) : (
        <>
          <PostList posts={feed.items} onDelete={handleDelete} onUpdated={handleUpdated} />
          <div className={styles.more}>
            {feed.hasMore ? (
              <Button
                variant="secondary"
                loading={feed.loadingMore}
                onClick={() =>
                  feed
                    .loadMore()
                    .catch((e) =>
                      toast.error(e instanceof ApiError ? e.message : 'Could not load more.'),
                    )
                }
              >
                Load more
              </Button>
            ) : (
              <p className={styles.end}>
                {searching ? 'End of results' : 'You’re all caught up'}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
