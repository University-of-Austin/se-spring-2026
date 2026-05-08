// All users, each clickable to their profile. Shows their post count too.
// Same three-branch (loading / error / data) shape as FeedPage.

import { useUsers } from '../hooks/useUsers'
import { UserLink } from '../components/UserLink'
import { Spinner } from '../components/Spinner'
import { ErrorMessage } from '../components/ErrorMessage'

export default function UserListPage() {
  const { users, loading, error } = useUsers()

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl">Users</h1>

      {loading && <Spinner />}
      {error && <ErrorMessage error={error} />}
      {!loading && !error && (
        users.length === 0
          ? <p className="text-muted">No users yet.</p>
          : <ul className="space-y-2">
              {users.map(u => (
                <li
                  key={u.username}
                  className="flex items-baseline justify-between border-b border-border pb-2"
                >
                  <UserLink username={u.username} />
                  <span className="text-sm text-muted font-mono">
                    {u.post_count} {u.post_count === 1 ? 'post' : 'posts'}
                  </span>
                </li>
              ))}
            </ul>
      )}
    </div>
  )
}
