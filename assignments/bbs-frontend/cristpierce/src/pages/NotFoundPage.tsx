import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/StateView'

export function NotFoundPage() {
  return (
    <EmptyState
      title="404 — page not found"
      hint={<Link to="/">Back to the feed →</Link>}
    />
  )
}
