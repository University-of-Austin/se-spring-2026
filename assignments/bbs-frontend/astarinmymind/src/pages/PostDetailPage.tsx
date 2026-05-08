// Placeholder. Real implementation in Phase 3: usePost hook + post details + delete button.
import { useParams } from 'react-router-dom'

export default function PostDetailPage() {
  const { id } = useParams()
  return <h1 className="font-serif text-3xl">Post #{id}</h1>
}
