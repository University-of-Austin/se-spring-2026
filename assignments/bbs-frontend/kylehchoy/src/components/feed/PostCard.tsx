import { Link } from 'react-router-dom'
import type { Post } from '../../api/types'
import { formatRelative } from '../../lib/formatTime'
import { ReactionBar } from '../reactions/ReactionBar'

/**
 * Single Wall post per the Variant C "Almanac" treatment.
 * Hairline ABOVE if not first in list; no boxes, no shadows, no card lift.
 * Eyebrow → body → reactions footer.
 */
export function PostCard({
  post,
  isFirst,
}: {
  post: Post
  isFirst?: boolean
}) {
  /** Negative IDs are optimistic temp posts (see useCreatePost). */
  const isOptimistic = post.id < 0

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
        {!isOptimistic && post.updated_at && post.updated_at !== post.created_at ? (
          <>
            <span style={dot}>·</span>
            <span style={{ fontStyle: 'italic', textTransform: 'none', letterSpacing: 'normal', fontFamily: 'var(--font-serif)', fontSize: 13 }}>
              edited
            </span>
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
        {post.snippet ? renderSnippet(post.snippet) : renderBody(post.message)}
      </div>

      {post.id > 0 ? <ReactionBar post={post} /> : null}

      <div style={footer}>
        <Link to={`/posts/${post.id}`} style={footerLink}>
          Open thread →
        </Link>
      </div>
    </article>
  )
}

/**
 * Render an A2 FTS5 snippet WITHOUT dangerouslySetInnerHTML.
 *
 * A2's snippet() carries two layers of content: the user-controlled
 * message body (which can contain literal angle brackets and HTML-like
 * substrings) plus <b>...</b> markers around bm25-matched terms inserted
 * by SQLite. The previous regex-strip approach was unsafe — the
 * negative-lookahead `b\b` treated a space as a word boundary, so
 * `<b onclick="alert(1)">` passed through and was rendered as raw HTML.
 *
 * Safer approach: split on the <b>...</b> markers, render text
 * fragments as React text (which escapes < / > / & automatically),
 * render bold fragments as <b> elements. No dangerouslySetInnerHTML
 * anywhere on this path.
 */
function renderSnippet(s: string): React.ReactNode {
  // Split keeps capturing groups, so we end up with alternating
  // [plain, '<b>match</b>', plain, '<b>match</b>', plain].
  const parts = s.split(/(<b>[\s\S]*?<\/b>)/gi)
  return parts.map((part, i) => {
    const m = part.match(/^<b>([\s\S]*?)<\/b>$/i)
    if (m) {
      return (
        <b key={i} style={{ background: 'var(--gold-tint)' }}>
          {m[1]}
        </b>
      )
    }
    return <span key={i}>{part}</span>
  })
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
