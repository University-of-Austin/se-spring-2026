import { useMountFetch } from '../hooks/useMountFetch'
import { bbsApi } from '../api/bbs'
import { FetchStateDisplay } from '../components/FetchStateDisplay'
import { Link } from 'react-router-dom'
import './pages.css'

export function UsersPage() {
  const { state, refetch } = useMountFetch('users', () => bbsApi.listUsers())

  return (
    <div className="page">
      <h1>Users</h1>
      <FetchStateDisplay state={state} onRetry={refetch}>
        {(users) =>
          users.length === 0 ? (
            <p className="empty-hint">No users registered yet.</p>
          ) : (
            <ul className="user-list">
              {users.map((u) => (
                <li key={u.username}>
                  <Link to={`/users/${encodeURIComponent(u.username)}`}>{u.username}</Link>
                  <span className="field-hint"> — joined {u.created_at}</span>
                </li>
              ))}
            </ul>
          )
        }
      </FetchStateDisplay>
    </div>
  )
}
