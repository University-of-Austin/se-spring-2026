import { useCallback, useEffect, useRef, useState } from 'react'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { useMountFetch } from '../hooks/useMountFetch'
import { useFeedOptimistic } from '../context/FeedOptimisticContext'
import { bbsApi } from '../api/bbs'
import { FetchStateDisplay } from '../components/FetchStateDisplay'
import { PostCard } from '../components/PostCard'
import './pages.css'

const PAGE_LIMIT = 20
const POLL_MS = 5000
const SCROLL_AWAY_PX = 160

type FeedPagedListProps = {
  qTrim: string
}

function listSignature(list: { id: number }[]): string {
  return list.map((p) => p.id).join(',')
}

function FeedPagedList({ qTrim }: FeedPagedListProps) {
  const [offset, setOffset] = useState(0)
  const { optimisticPost, registerFeedRefetch } = useFeedOptimistic()
  const [scrolledAway, setScrolledAway] = useState(false)
  const [showNewPostsBanner, setShowNewPostsBanner] = useState(false)
  const baselineSigRef = useRef<string>('')

  const cacheKey = `posts:${qTrim}:${PAGE_LIMIT}:${offset}`

  const { state, refetch } = useMountFetch(cacheKey, () =>
    bbsApi.listPosts({
      ...(qTrim ? { q: qTrim } : {}),
      limit: PAGE_LIMIT,
      offset,
    }),
  )

  const feedListSig = state.phase === 'success' ? listSignature(state.data) : null

  useEffect(() => {
    return registerFeedRefetch(refetch)
  }, [registerFeedRefetch, refetch])

  useEffect(() => {
    const id = window.setInterval(() => {
      void refetch()
    }, POLL_MS)
    return () => window.clearInterval(id)
  }, [refetch])

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY || document.documentElement.scrollTop
      const away = y > SCROLL_AWAY_PX
      setScrolledAway(away)
      if (!away) {
        setShowNewPostsBanner(false)
      }
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (feedListSig === null) {
      return
    }
    if (offset !== 0) {
      baselineSigRef.current = feedListSig
      return
    }
    if (baselineSigRef.current !== '' && baselineSigRef.current !== feedListSig && scrolledAway) {
      setShowNewPostsBanner(true)
    }
    if (!scrolledAway) {
      baselineSigRef.current = feedListSig
    }
  }, [feedListSig, offset, scrolledAway])

  const onNewPostsClick = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    setShowNewPostsBanner(false)
    if (state.phase === 'success') {
      baselineSigRef.current = listSignature(state.data)
    }
  }, [state])

  const canPrev = offset > 0
  const posts = state.phase === 'success' ? state.data : []
  const canNext = state.phase === 'success' && posts.length === PAGE_LIMIT

  return (
    <>
      {showNewPostsBanner && offset === 0 ? (
        <div className="feed-new-posts-banner" role="status">
          <button type="button" className="feed-new-posts-banner__btn" onClick={onNewPostsClick}>
            New posts available — jump to top
          </button>
        </div>
      ) : null}
      <div className="feed-pagination">
        <button
          type="button"
          className="btn btn-secondary"
          disabled={!canPrev}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE_LIMIT))}
        >
          Previous
        </button>
        <span className="feed-pagination__meta">
          {posts.length > 0
            ? `Rows ${offset + 1}–${offset + posts.length}`
            : `No posts (offset ${offset})`}
          {qTrim ? ` · filter “${qTrim}”` : ''}
        </span>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={!canNext}
          onClick={() => setOffset((o) => o + PAGE_LIMIT)}
        >
          Next
        </button>
      </div>
      <FetchStateDisplay state={state} onRetry={refetch}>
        {(list) => {
          const merged =
            optimisticPost && optimisticPost.id < 0
              ? [optimisticPost, ...list.filter((p) => p.id !== optimisticPost.id)]
              : list
          return merged.length === 0 ? (
            <p className="empty-hint">No posts on this page.</p>
          ) : (
            <ul className="post-list">
              {merged.map((p) => (
                <PostCard key={p.id} post={p} />
              ))}
            </ul>
          )
        }}
      </FetchStateDisplay>
    </>
  )
}

export function FeedPage() {
  const [searchRaw, setSearchRaw] = useState('')
  const debouncedSearch = useDebouncedValue(searchRaw, 300)
  const qTrim = debouncedSearch.trim()

  return (
    <div className="page">
      <h1>Feed</h1>
      <div className="field feed-search">
        <label htmlFor="feed-search">Search posts</label>
        <input
          id="feed-search"
          type="search"
          value={searchRaw}
          onChange={(e) => setSearchRaw(e.target.value)}
          placeholder="Filter by message text…"
          autoComplete="off"
        />
      </div>
      <FeedPagedList key={qTrim} qTrim={qTrim} />
    </div>
  )
}
