import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getTrending } from '../../api/posts'

/**
 * Sidebar widget surfacing GET /posts/trending — A2's popularity
 * ranking shortcut (sort=top with a 24h default window). Five posts
 * max so the sidebar stays typographic, not data-dense.
 */
export function TrendingWidget({ window = 24 }: { window?: number }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['trending', window],
    queryFn: () => getTrending({ window, limit: 5 }),
    staleTime: 60_000,
  })

  if (isError) return null

  return (
    <section style={{ marginBottom: 40 }}>
      <h2 style={head}>Trending · {window}h</h2>
      {isLoading || !data ? (
        <p style={mutedItalic}>…</p>
      ) : data.length === 0 ? (
        <p style={mutedItalic}>Nothing ranked yet.</p>
      ) : (
        <ol style={list}>
          {data.map((post, i) => {
            const total = post.reaction_counts.like + post.reaction_counts.laugh + post.reaction_counts.heart
            const excerpt = post.message.replace(/\s+/g, ' ').slice(0, 70)
            return (
              <li key={post.id} style={item}>
                <span style={rank}>{i + 1}.</span>
                <Link to={`/posts/${post.id}`} style={titleLink}>
                  {excerpt}{post.message.length > 70 ? '…' : ''}
                </Link>
                <div style={meta}>
                  @{post.username} · {total} {total === 1 ? 'reaction' : 'reactions'}
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}

const head: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.2em',
  textTransform: 'uppercase',
  color: 'var(--black)',
  paddingBottom: 6,
  borderBottom: '1px solid var(--gold)',
  marginBottom: 14,
  fontWeight: 500,
}

const mutedItalic: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 13,
  color: 'var(--muted)',
}

const list: React.CSSProperties = { listStyle: 'none', padding: 0, margin: 0 }
const item: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '20px 1fr',
  gap: 6,
  marginBottom: 16,
}
const rank: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontSize: 14,
  fontStyle: 'italic',
  color: 'var(--gold)',
  lineHeight: 1.4,
}
const titleLink: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontSize: 14,
  lineHeight: 1.4,
  color: 'var(--black)',
  textDecoration: 'none',
}
const meta: React.CSSProperties = {
  gridColumn: '2',
  marginTop: 2,
  fontFamily: 'var(--font-sans)',
  fontSize: 9,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
}
