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

type SortMode = 'recent' | 'top'
type TopWindow = 24 | 168 | 720 // hours: 24h / 7d / 30d

export default function FeedPage() {
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState<string | null>(null)
  const [accumulated, setAccumulated] = useState<Post[]>([])
  const [sort, setSort] = useState<SortMode>('recent')
  const [topWindow, setTopWindow] = useState<TopWindow>(24)
  const debouncedQuery = useDebouncedValue(query, 300)
  const searchRef = useRef<HTMLInputElement | null>(null)

  const focusSearch = useCallback(() => {
    searchRef.current?.focus()
    searchRef.current?.select()
  }, [])
  useKeyboardShortcut('/', focusSearch)

  // Reset cursor when switching sort modes — A2 returns 422 on
  // sort=top + cursor (bm25 rank isn't monotonic).
  useEffect(() => {
    setCursor(null)
    setAccumulated([])
  }, [sort, topWindow])

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
  // Sort=top also pauses polling because trending output is meant to
  // be a snapshot, not a live stream.
  const refetchInterval = usePolling(5000)
  const shouldPoll = sort === 'recent' && cursor === null && !debouncedQuery

  const { data, isLoading, isFetching, isError, error, refetch } = useQuery<ListPostsResponse>({
    queryKey: ['posts', { q: debouncedQuery, cursor, sort, window: topWindow }],
    queryFn: () =>
      listPosts({
        q: debouncedQuery || undefined,
        // A2 rejects cursor + q (422) and cursor + sort=top (422).
        // Use offset path when searching or sorting by top.
        cursor: debouncedQuery || sort === 'top' ? undefined : cursor ?? undefined,
        sort: sort === 'top' ? 'top' : undefined,
        window: sort === 'top' ? topWindow : undefined,
        limit: 25,
      }),
    refetchInterval: shouldPoll ? refetchInterval : false,
    refetchIntervalInBackground: false,
  })

  // Merge cursor-paginated pages into accumulated. Only for the
  // recent/no-search path — search and trending return their own
  // fresh list every fetch.
  useEffect(() => {
    if (!data || debouncedQuery || sort === 'top') return
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
  }, [data, debouncedQuery, cursor, sort])

  const displayed = debouncedQuery || sort === 'top' ? data?.posts ?? [] : accumulated

  return (
    <div style={wrap} data-shell="two-col">
      <main>
        <SearchBox value={query} onChange={setQuery} inputRef={searchRef} />
        <SortBar
          sort={sort}
          onSortChange={setSort}
          topWindow={topWindow}
          onWindowChange={setTopWindow}
        />

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

        {!debouncedQuery && sort === 'recent' && data?.next_cursor ? (
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

function SortBar({
  sort,
  onSortChange,
  topWindow,
  onWindowChange,
}: {
  sort: SortMode
  onSortChange: (s: SortMode) => void
  topWindow: TopWindow
  onWindowChange: (w: TopWindow) => void
}) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 24,
        alignItems: 'baseline',
        marginBottom: 24,
        paddingBottom: 12,
        borderBottom: '1px solid var(--hairline)',
        flexWrap: 'wrap',
      }}
    >
      <span style={sortLabel}>Sort</span>
      <button type="button" onClick={() => onSortChange('recent')} style={tab(sort === 'recent')} aria-pressed={sort === 'recent'}>
        Recent
      </button>
      <button type="button" onClick={() => onSortChange('top')} style={tab(sort === 'top')} aria-pressed={sort === 'top'}>
        Trending
      </button>
      {sort === 'top' ? (
        <>
          <span style={{ ...sortLabel, marginLeft: 'auto' }}>Window</span>
          {([24, 168, 720] as const).map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => onWindowChange(w as TopWindow)}
              style={tab(topWindow === w, true)}
              aria-pressed={topWindow === w}
            >
              {w === 24 ? '24h' : w === 168 ? '7d' : '30d'}
            </button>
          ))}
        </>
      ) : null}
    </div>
  )
}

const sortLabel: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.2em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
}
function tab(active: boolean, small = false): React.CSSProperties {
  return {
    fontFamily: 'var(--font-sans)',
    fontSize: small ? 9 : 11,
    letterSpacing: '0.16em',
    textTransform: 'uppercase',
    color: active ? 'var(--black)' : 'var(--muted)',
    background: 'transparent',
    border: 0,
    padding: '2px 0',
    borderBottom: active ? '2px solid var(--gold)' : '2px solid transparent',
    cursor: 'pointer',
  }
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
