/**
 * Phase 0 boot page.
 * Confirms: Newsreader serif loads, Antonio loads, cream + gold palette renders,
 * Tailwind v4 + tokens are wired. Real app shell + routing arrives in Phase 2.
 */
export default function App() {
  return (
    <>
      <header
        style={{
          background: 'var(--gold)',
          height: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          color: 'var(--white)',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 24,
            fontWeight: 500,
          }}
        >
          thenetwork
        </span>
        <span
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 11,
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
          }}
        >
          Phase 0 · boot
        </span>
      </header>

      <main
        style={{
          maxWidth: 580,
          margin: '0 auto',
          padding: '48px 24px 64px',
        }}
      >
        <p
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 11,
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            color: 'var(--muted)',
            marginBottom: 14,
          }}
        >
          Wall · Boot Check · 0h ago
        </p>

        <h1
          style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 32,
            fontWeight: 500,
            lineHeight: 1.1,
            marginBottom: 24,
          }}
        >
          Dare to think. Dare to post.
        </h1>

        <p
          style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 17,
            lineHeight: 1.55,
          }}
        >
          If you are reading this in serif type on cream paper with the gold
          masthead above it, Phase 0 has shipped. Newsreader loaded.
          Antonio loaded. Tokens wired. The next phase is the API client,
          identity context, and routing.
        </p>

        <p
          style={{
            marginTop: 24,
            fontFamily: 'var(--font-sans)',
            fontSize: 10,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: 'var(--muted)',
          }}
        >
          A UATX Student Production · An online directory · Not a feed
        </p>
      </main>
    </>
  )
}
