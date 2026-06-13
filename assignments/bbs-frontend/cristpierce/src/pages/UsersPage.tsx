import { Link } from 'react-router-dom'
import { useUsers } from '../hooks/resources'
import { relativeTime } from '../lib/time'
import { Avatar } from '../components/Avatar'
import { PageHeader } from '../components/PageBits'
import { Button } from '../components/ui/Button'
import { EmptyState, LoadingBlock, StateView } from '../components/ui/StateView'
import { PlusIcon } from '../components/ui/icons'
import styles from './UsersPage.module.css'

export function UsersPage() {
  const users = useUsers()

  return (
    <div>
      <PageHeader
        title="Users"
        subtitle="Everyone on the board"
        actions={
          <Link to="/login">
            <Button variant="secondary" size="sm">
              <PlusIcon size={15} />
              New user
            </Button>
          </Link>
        }
      />

      <StateView
        status={users.status}
        data={users.data}
        error={users.error}
        onRetry={users.refetch}
        errorTitle="Couldn’t load users"
        loading={<LoadingBlock label="Loading users…" />}
        isEmpty={(list) => list.length === 0}
        empty={
          <EmptyState title="No users yet" hint={<Link to="/login">Create the first one →</Link>} />
        }
      >
        {(list) => (
          <ul className={styles.list}>
            {list.map((u) => (
              <li key={u.username}>
                <Link to={`/users/${u.username}`} className={styles.row}>
                  <Avatar username={u.username} size={40} />
                  <div className={styles.meta}>
                    <span className={styles.name}>{u.username}</span>
                    <span className={styles.sub}>joined {relativeTime(u.created_at)}</span>
                  </div>
                  <span className={styles.count}>
                    {u.post_count} {u.post_count === 1 ? 'post' : 'posts'}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </StateView>
    </div>
  )
}
