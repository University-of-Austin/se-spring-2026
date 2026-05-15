import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listUsers } from '../../api/users'
import { useIdentity } from '../../auth/IdentityContext'

/**
 * Right sidebar on the Feed page.
 * Typographic — no boxes, no panels. Tracked uppercase Antonio headers
 * with `border-bottom: 1px solid var(--gold)`; content beneath in
 * Newsreader (large numerals + small-caps usernames).
 */
export function FeedSidebar() {
  const { username } = useIdentity()
  const { data: users = [] } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers(100, 0),
    staleTime: 60_000,
  })

  const total = users.length
  const recentlyOnline = users.slice(0, 5)

  return (
    <aside>
      <Section title="The Network">
        <Stat num={total} sub="students in the directory" />
      </Section>

      <Section title="Recently Joined">
        {recentlyOnline.length === 0 ? (
          <p style={mutedItalic}>No one yet.</p>
        ) : (
          <ul style={list}>
            {recentlyOnline.map((u) => (
              <li key={u.username} style={listItem}>
                <span style={dot} aria-hidden="true" />
                <Link
                  to={`/users/${encodeURIComponent(u.username)}`}
                  style={{ color: 'var(--black)', textDecoration: 'none' }}
                >
                  @{u.username}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {username ? (
        <Section title="You">
          <p style={mutedItalic}>
            Posting as <strong style={{ color: 'var(--black)', fontStyle: 'normal' }}>@{username}</strong>.{' '}
            <Link to="/signup" style={{ color: 'var(--gold)' }}>
              Switch →
            </Link>
          </p>
        </Section>
      ) : (
        <Section title="Identity">
          <p style={mutedItalic}>
            <Link to="/signup" style={{ color: 'var(--gold)' }}>
              Join the Network →
            </Link>
          </p>
        </Section>
      )}
    </aside>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 40 }}>
      <h2
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 10,
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          color: 'var(--black)',
          paddingBottom: 6,
          borderBottom: '1px solid var(--gold)',
          marginBottom: 14,
          fontWeight: 500,
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  )
}

function Stat({ num, sub }: { num: number | string; sub: string }) {
  return (
    <>
      <div
        style={{
          fontFamily: 'var(--font-serif)',
          fontSize: 40,
          lineHeight: 1,
          color: 'var(--black)',
          letterSpacing: '-0.01em',
        }}
      >
        {num}
      </div>
      <div
        style={{
          fontFamily: 'var(--font-serif)',
          fontStyle: 'italic',
          fontSize: 13,
          color: 'var(--muted)',
          marginTop: 4,
        }}
      >
        {sub}
      </div>
    </>
  )
}

const list: React.CSSProperties = { listStyle: 'none', padding: 0, margin: 0 }
const listItem: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontSize: 14,
  lineHeight: 1.9,
  fontVariant: 'small-caps',
  letterSpacing: '0.02em',
  display: 'flex',
  alignItems: 'baseline',
  gap: 8,
  color: 'var(--black)',
}
const dot: React.CSSProperties = {
  display: 'inline-block',
  width: 6,
  height: 6,
  background: 'var(--gold)',
  borderRadius: '50%',
  flexShrink: 0,
}
const mutedItalic: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 14,
  color: 'var(--muted)',
}
