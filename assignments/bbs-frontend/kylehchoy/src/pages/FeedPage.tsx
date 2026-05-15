import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listPosts } from '../api/posts'
import type { ListPostsResponse, Post } from '../api/types'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { usePolling } from '../hooks/usePolling'
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut'
import { ComposeBox } from '../components/feed/ComposeBox'
import { PostCard } from '../components/feed/PostCard'
import { FeedSidebar } from '../components/feed/Sidebar'
import { LoadingRow, ErrorBanner, EmptyState } from '../components/states/States'

export default function FeedPage() {
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState<string | null>(null)
  const [accumulated, setAccumulated] = useState<Post[]>([])
  const debouncedQuery = useDebouncedValue(query, 300)
  const searchRef = useRef<HTMLInputElement | null>(null)

  const focusSearch = useCallback(() => {
    searchRef.current?.focus()
    searchRef.current?.select()
  }, [])
  useKeyboardShortcut('/', focusSearch)

  // Reset accumulation when search changes (search uses offset, not cursor).
  const prevQ = useRef(debouncedQuery)
  useEffect(() => {
    if (prevQ.current !== debouncedQuery) {
      setAccumulated([])
      setCursor(null)
      prevQ.current = debouncedQuery
    }
  }, [debouncedQuery])

  // Poll the top of the feed only — once the user has paged into older
  // posts (cursor != null), pause polling to avoid clobbering scroll.
  const refetchInterval = usePolling(5000)
  const shouldPoll = cursor === null && !debouncedQuery

  const { data, isLoading, isFetching, isError, error, refetch } = useQuery<ListPostsResponse>({
    queryKey: ['posts', { q: debouncedQuery, cursor }],
    queryFn: () =>
      listPosts({
        q: debouncedQuery || undefined,
        // A2 rejects cursor + q (422). Drop cursor when searching.
        cursor: debouncedQuery ? undefined : cursor ?? undefined,
        limit: 25,
      }),
    refetchInterval: shouldPoll ? refetchInterval : false,
    refetchIntervalInBackground: false,
  })

  // Merge cursor-paginated pages into accumulated.
  useEffect(() => {
    if (!data || debouncedQuery) return
    if (cursor === null) {
      setAccumulated(data.posts)
    } else {
      setAccumulated((prev) => {
        const seen = new Set(prev.map((p) => p.id))
        const merged = [...prev]
        for (const p of data.posts) if (!seen.has(p.id)) merged.push(p)
        return merged
      })
    }
  }, [data, debouncedQuery, cursor])

  const displayed = debouncedQuery ? data?.posts ?? [] : accumulated

  return (
    <div style={wrap} data-shell="two-col">
      <main>
        <SearchBox value={query} onChange={setQuery} inputRef={searchRef} />

        <ComposeBox />

        {isLoading && displayed.length === 0 ? (
          <>
            <LoadingRow label="The Wall" />
            <LoadingRow label="More" />
          </>
        ) : null}

        {isError ? <ErrorBanner error={error} onRetry={() => void refetch()} /> : null}

        {!isLoading && !isError && displayed.length === 0 ? (
          <EmptyState title="No posts on the Wall yet">
            {debouncedQuery ? <>Nothing matches "{debouncedQuery}".</> : <>Be the first to post.</>}
          </EmptyState>
        ) : null}

        {displayed.map((p, i) => (
          <PostCard key={p.id} post={p} isFirst={i === 0} />
        ))}

        {!debouncedQuery && data?.next_cursor ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <button
              type="button"
              onClick={() => setCursor(data.next_cursor)}
              disabled={isFetching}
              style={loadMoreBtn}
            >
              {isFetching ? 'Loading…' : 'Load more'}
            </button>
          </div>
        ) : null}
      </main>

      <FeedSidebar />
    </div>
  )
}

function SearchBox({
  value,
  onChange,
  inputRef,
}: {
  value: string
  onChange: (v: string) => void
  inputRef?: React.RefObject<HTMLInputElement | null>
}) {
  return (
    <div style={{ marginBottom: 24 }}>
      <label
        htmlFor="search-wall"
        style={{
          display: 'block',
          fontFamily: 'var(--font-sans)',
          fontSize: 10,
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          color: 'var(--muted)',
          marginBottom: 8,
        }}
      >
        Search the Directory <span style={{ color: 'var(--hairline)' }}>· press /</span>
      </label>
      <input
        id="search-wall"
        ref={inputRef}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Find a post…"
        style={{
          width: '100%',
          fontFamily: 'var(--font-serif)',
          fontSize: 15,
          color: 'var(--black)',
          background: 'transparent',
          border: 'none',
          borderBottom: '1px solid var(--hairline)',
          padding: '6px 0',
          outline: 'none',
        }}
      />
    </div>
  )
}

const wrap: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '580px 200px',
  gap: 48,
  maxWidth: 860,
  margin: '0 auto',
  padding: '48px 24px 56px',
}

const loadMoreBtn: React.CSSProperties = {
  background: 'transparent',
  color: 'var(--gold)',
  border: '1px solid var(--gold)',
  padding: '8px 24px',
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  cursor: 'pointer',
}
