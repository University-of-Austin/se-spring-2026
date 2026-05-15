import { Link } from 'react-router-dom'
import type { Post } from '../../api/types'
import { formatRelative } from '../../lib/formatTime'

/**
 * Single Wall post per the Variant C "Almanac" treatment.
 * Hairline ABOVE if not first in list; no boxes, no shadows, no card lift.
 * Eyebrow → body → reactions footer.
 */
export function PostCard({
  post,
  isFirst,
  isOptimistic = false,
}: {
  post: Post
  isFirst?: boolean
  isOptimistic?: boolean
}) {
  const replyCount = post.snippet ? undefined : undefined
  // ^ replyCount comes from a separate endpoint; show "N Notes" only when known.
  // Keep eyebrow clean for now.

  return (
    <article
      style={{
        padding: '0 0 32px 0',
        marginTop: isFirst ? 0 : 32,
        borderTop: isFirst ? 'none' : '1px solid var(--hairline)',
        paddingTop: isFirst ? 0 : 32,
        opacity: isOptimistic ? 0.55 : 1,
        transition: 'opacity 200ms ease-out',
      }}
    >
      <div style={eyebrow}>
        <span>Wall</span>
        <span style={dot}>·</span>
        <span>{formatRelative(post.created_at)}</span>
        <span style={dot}>·</span>
        <Link
          to={`/users/${encodeURIComponent(post.username)}`}
          style={{ color: 'var(--black)', fontWeight: 500, textDecoration: 'underline', textUnderlineOffset: 2 }}
        >
          @{post.username}
        </Link>
        {replyCount !== undefined ? (
          <>
            <span style={dot}>·</span>
            <span>{replyCount} notes</span>
          </>
        ) : null}
        {isOptimistic ? (
          <>
            <span style={dot}>·</span>
            <span style={{ fontStyle: 'italic' }}>posting…</span>
          </>
        ) : null}
      </div>

      <div style={body}>
        {post.snippet ? (
          <span dangerouslySetInnerHTML={{ __html: sanitizeSnippet(post.snippet) }} />
        ) : (
          renderBody(post.message)
        )}
      </div>

      <div style={footer}>
        <Link to={`/posts/${post.id}`} style={footerLink}>
          Open thread
        </Link>
      </div>
    </article>
  )
}

/** Allow only <b>…</b> from FTS snippets; strip everything else. */
function sanitizeSnippet(s: string): string {
  return s
    .replace(/<(?!\/?b\b)[^>]*>/gi, '')
    .replace(/<b>/gi, '<b style="background: var(--gold-tint);">')
}

/** Break body into <p>s on blank lines so eyebrow / serif rhythm holds. */
function renderBody(message: string): React.ReactNode {
  const paragraphs = message.split(/\n\s*\n/)
  return paragraphs.map((p, i) => (
    <p key={i} style={{ marginTop: i === 0 ? 0 : '0.6em' }}>
      {p}
    </p>
  ))
}

const eyebrow: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.16em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  marginBottom: 14,
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  alignItems: 'baseline',
}

const dot: React.CSSProperties = {
  color: 'var(--gold)',
}

const body: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontSize: 17,
  lineHeight: 1.55,
  color: 'var(--black)',
}

const footer: React.CSSProperties = {
  marginTop: 16,
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  display: 'flex',
  gap: 18,
}

const footerLink: React.CSSProperties = {
  textDecoration: 'none',
  color: 'var(--muted)',
}
