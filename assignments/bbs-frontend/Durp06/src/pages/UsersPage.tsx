import { Link } from 'react-router-dom';
import { useUsers } from '../hooks/useUsers';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';

export default function UsersPage() {
  const { data, loading, error, refetch } = useUsers();

  return (
    <section className="page page--users">
      <header className="page__head">
        <h1>Users</h1>
        <Link to="/signup" className="btn btn--primary btn--sm">
          Create user
        </Link>
      </header>

      {loading && <Loading label="Loading users" />}
      {error && <ErrorMessage message={error} onRetry={refetch} />}
      {data && data.length === 0 && <p className="empty">No users yet.</p>}
      {data && data.length > 0 && (
        <ul className="user-list" aria-label="Users">
          {data.map((u) => (
            <li key={u.username} className="user-list__item">
              <Link to={`/users/${encodeURIComponent(u.username)}`} className="user-list__link">
                <span className="user-list__name">@{u.username}</span>
                <span className="user-list__meta">
                  {u.post_count} post{u.post_count === 1 ? '' : 's'}
                </span>
              </Link>
              {u.bio && <p className="user-list__bio">{u.bio}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
