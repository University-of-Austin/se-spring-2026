// Catch-all for unknown routes (anything not matched by the other Routes).
import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="text-center py-16">
      <h1 className="font-serif text-4xl">404</h1>
      <p className="mt-4 text-muted">That page doesn't exist.</p>
      <Link to="/" className="mt-6 inline-block text-accent hover:underline">
        Back to feed →
      </Link>
    </div>
  )
}
