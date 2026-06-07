import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import type { Post } from '../../api/types'
import { listReplies } from '../../api/posts'
import { ReactionBar } from '../reactions/ReactionBar'
import { formatRelative } from '../../lib/formatTime'
import { ReplyComposer } from './ReplyComposer'

/**
 * One reply, plus (lazily) its own children when expanded.
 * Recursive — children render as ReplyCard too, indented one notch.
 * Depth cap: visual indent stops at 3 levels (collapses to 16px gutter)
 * to keep narrow viewports usable.
 */
export function ReplyCard({
  post,
  depth = 0,
  isNew = false,
}: {
  post: Post
  depth?: number
  isNew?: boolean
}) {
  const [composing, setComposing] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const isOptimistic = post.id < 0

  const repliesQ = useQuery({
    queryKey: ['post', post.id, 'replies'],
    queryFn: () => listReplies(post.id, 50, 0),
    enabled: expanded && !isOptimistic,
    staleTime: 15_000,
  })

  const indentPx = Math.min(depth, 3) * 24

  return (
    <li
      style={{
        marginLeft: indentPx,
        paddingTop: 20,
        paddingBottom: 20,
        borderTop: depth > 0 ? '1px solid var(--hairline)' : 'none',
        opacity: isOptimistic ? 0.55 : 1,
        animation: isNew ? 'replyArrive 250ms ease-out' : 'none',
      }}
    >
      <style>{`
        @keyframes replyArrive {
          from { opacity: 0; transform: translateX(-12px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>

      <div style={eyebrow}>
        <span>Reply</span>
        <span style={dotG}>·</span>
        <span>{formatRelative(post.created_at)}</span>
        <span style={dotG}>·</span>
        <Link
          to={`/users/${encodeURIComponent(post.username)}`}
          style={{ color: 'var(--black)', fontWeight: 500 }}
        >
          @{post.username}
        </Link>
        {isOptimistic ? (
          <>
            <span style={dotG}>·</span>
            <span style={{ fontStyle: 'italic' }}>posting…</span>
          </>
        ) : null}
      </div>

      <div style={body}>
        {post.message.split(/\n\s*\n/).map((p, i) => (
          <p key={i} style={{ marginTop: i === 0 ? 0 : '0.5em' }}>{p}</p>
        ))}
      </div>

      {!isOptimistic ? (
        <>
          <ReactionBar post={post} />

          <div style={controls}>
            <button
              type="button"
              onClick={() => setComposing((c) => !c)}
              style={ctrlBtn}
              aria-pressed={composing}
            >
              {composing ? 'Close' : 'Reply'}
            </button>
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              style={ctrlBtn}
              aria-expanded={expanded}
            >
              {expanded ? '▼ Replies' : '▶ Replies'}
            </button>
          </div>
        </>
      ) : null}

      {composing ? (
        <ReplyComposer
          parentId={post.id}
          onDone={() => setComposing(false)}
        />
      ) : null}

      {expanded && repliesQ.data && repliesQ.data.length > 0 ? (
        <ul style={childList}>
          {repliesQ.data.map((r) => (
            <ReplyCard key={r.id} post={r} depth={depth + 1} />
          ))}
        </ul>
      ) : null}
      {expanded && repliesQ.data && repliesQ.data.length === 0 ? (
        <p style={emptyChild}>No replies on this branch yet.</p>
      ) : null}
    </li>
  )
}

const eyebrow: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  marginBottom: 10,
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  alignItems: 'baseline',
}

const dotG: React.CSSProperties = { color: 'var(--gold)' }

const body: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontSize: 16,
  lineHeight: 1.55,
  color: 'var(--black)',
}

const controls: React.CSSProperties = {
  marginTop: 12,
  display: 'flex',
  gap: 18,
}

const ctrlBtn: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  background: 'transparent',
  border: 0,
  padding: 0,
  cursor: 'pointer',
}

const childList: React.CSSProperties = {
  listStyle: 'none',
  padding: 0,
  margin: '16px 0 0 0',
  borderLeft: '1px solid var(--gold)',
  paddingLeft: 16,
}

const emptyChild: React.CSSProperties = {
  marginTop: 12,
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 13,
  color: 'var(--muted)',
}
