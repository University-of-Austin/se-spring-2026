import { useParams } from 'react-router-dom'

export default function PostDetailPage() {
  const { id } = useParams<{ id: string }>()
  return (
    <div style={{ maxWidth: 580, margin: '0 auto', padding: '48px 24px' }}>
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
        Live Thread · № {id} · Phase 2 stub
      </p>
      <p style={{ fontFamily: 'var(--font-serif)', fontSize: 17, lineHeight: 1.55 }}>
        Thread tree + replies + reactions land in Phase 7 (the Live Thread gold feature).
      </p>
    </div>
  )
}
