import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listReplies } from '../../api/posts'
import { usePolling } from '../../hooks/usePolling'
import { LoadingRow, ErrorBanner, EmptyState } from '../states/States'
import { ReplyCard } from './ReplyCard'
import { ReplyComposer } from './ReplyComposer'

/**
 * Top-level replies under a root post. Polled every 5s when visible.
 * Diffs against the previous fetch so new replies get a one-shot
 * "arrive" animation — the polled-live feel.
 */
export function ReplyTree({ rootId }: { rootId: number }) {
  const refetchInterval = usePolling(5000)
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['post', rootId, 'replies'],
    queryFn: () => listReplies(rootId, 100, 0),
    refetchInterval,
    refetchIntervalInBackground: false,
  })

  // Track which IDs are new since the previous render so we can apply
  // the arrival animation just once per ID.
  const seen = useRef<Set<number>>(new Set())
  const arrived = useRef<Set<number>>(new Set())
  useEffect(() => {
    if (!data) return
    const next = new Set<number>()
    const newlyArrived = new Set<number>()
    for (const r of data) {
      if (!seen.current.has(r.id) && seen.current.size > 0) {
        newlyArrived.add(r.id)
      }
      next.add(r.id)
    }
    seen.current = next
    arrived.current = newlyArrived
  }, [data])

  return (
    <section aria-label="Replies">
      <h2 style={head}>
        The Thread
        {data ? <span style={count}>· {data.length} replies</span> : null}
      </h2>

      <ReplyComposer parentId={rootId} />

      {isLoading ? <LoadingRow label="Replies" /> : null}
      {isError ? <ErrorBanner error={error} onRetry={() => void refetch()} /> : null}
      {!isLoading && !isError && data && data.length === 0 ? (
        <EmptyState title="No replies yet">First in is first to argue.</EmptyState>
      ) : null}

      {data && data.length > 0 ? (
        <ul style={list}>
          {data.map((r) => (
            <ReplyCard key={r.id} post={r} isNew={arrived.current.has(r.id)} />
          ))}
        </ul>
      ) : null}
    </section>
  )
}

const head: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.2em',
  textTransform: 'uppercase',
  color: 'var(--black)',
  borderBottom: '1px solid var(--gold)',
  paddingBottom: 8,
  marginTop: 40,
  marginBottom: 24,
  fontWeight: 500,
  display: 'flex',
  alignItems: 'baseline',
  gap: 10,
}

const count: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 13,
  color: 'var(--muted)',
  letterSpacing: 'normal',
  textTransform: 'none',
}

const list: React.CSSProperties = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
}
