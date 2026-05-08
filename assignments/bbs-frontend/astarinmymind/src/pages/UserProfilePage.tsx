// Placeholder. Real implementation in Phase 3: useUser hook + user info + their posts.
import { useParams } from 'react-router-dom'

export default function UserProfilePage() {
  const { username } = useParams()
  return <h1 className="font-serif text-3xl">User: @{username}</h1>
}
