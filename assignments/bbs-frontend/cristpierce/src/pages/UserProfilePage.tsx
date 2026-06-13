import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../lib/api'
import type { Post } from '../lib/types'
import { LIMITS } from '../lib/types'
import { useUser, useUserPosts } from '../hooks/resources'
import { absoluteTime, relativeTime } from '../lib/time'
import { useIdentity } from '../context/IdentityContext'
import { useToast } from '../context/ToastContext'
import { Avatar } from '../components/Avatar'
import { PostList } from '../components/PostList'
import { BackLink } from '../components/PageBits'
import { Button } from '../components/ui/Button'
import { CharCounter } from '../components/CharCounter'
import { EmptyState, LoadingBlock, StateView } from '../components/ui/StateView'
import { PostCardSkeleton } from '../components/ui/Skeleton'
import styles from './UserProfilePage.module.css'

export function UserProfilePage() {
  const { username = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { username: me, logout } = useIdentity()

  const user = useUser(username)
  const posts = useUserPosts(username)

  const [editingBio, setEditingBio] = useState(false)
  const [bioDraft, setBioDraft] = useState('')
  const [savingBio, setSavingBio] = useState(false)
  const [bioError, setBioError] = useState<string | null>(null)

  const isOwn = me !== null && me === username

  async function handleDelete(post: Post) {
    const snapshot = posts.data ?? []
    posts.setData(snapshot.filter((p) => p.id !== post.id))
    try {
      await api.deletePost(post.id)
    } catch (err) {
      posts.setData(snapshot)
      toast.error(err instanceof ApiError ? err.message : 'Could not delete the post.')
    }
  }

  function handleUpdated(updated: Post) {
    posts.setData((cur) => (cur ?? []).map((p) => (p.id === updated.id ? updated : p)))
  }

  async function saveBio() {
    if (!user.data || bioDraft.length > LIMITS.bioMax) return
    setSavingBio(true)
    setBioError(null)
    try {
      const updated = await api.updateBio(username, bioDraft)
      user.setData(updated)
      setEditingBio(false)
      toast.success('Bio updated.')
    } catch (err) {
      setBioError(err instanceof ApiError ? err.message : 'Could not save bio.')
    } finally {
      setSavingBio(false)
    }
  }

  // Dedicated 404 view (all hooks above already ran, so this early return is safe).
  if (user.isError && user.error?.status === 404) {
    return (
      <div>
        <BackLink to="/users">All users</BackLink>
        <EmptyState
          title={`No user “${username}”`}
          hint={<Link to="/users">Browse all users →</Link>}
        />
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <BackLink to="/users">All users</BackLink>

      <StateView
        status={user.status}
        data={user.data}
        error={user.error}
        onRetry={user.refetch}
        errorTitle="Couldn’t load this profile"
        loading={<LoadingBlock label="Loading profile…" />}
      >
        {(u) => (
          <header className={styles.profile}>
            <Avatar username={u.username} size={64} />
            <div className={styles.info}>
              <h1 className={styles.name}>{u.username}</h1>
              <p className={styles.stats}>
                <span>
                  {u.post_count} {u.post_count === 1 ? 'post' : 'posts'}
                </span>
                <span aria-hidden="true"> · </span>
                <span title={absoluteTime(u.created_at)}>joined {relativeTime(u.created_at)}</span>
              </p>

              {editingBio ? (
                <div className={styles.bioEdit}>
                  <label htmlFor="bio-input" className="visually-hidden">
                    Your bio
                  </label>
                  <textarea
                    id="bio-input"
                    className={styles.bioInput}
                    value={bioDraft}
                    rows={2}
                    maxLength={LIMITS.bioMax + 50}
                    placeholder="Say something about yourself…"
                    aria-invalid={bioDraft.length > LIMITS.bioMax || bioError !== null}
                    onChange={(e) => {
                      setBioDraft(e.target.value)
                      setBioError(null)
                    }}
                  />
                  {bioError && (
                    <p className={styles.bioError} role="alert">
                      {bioError}
                    </p>
                  )}
                  <div className={styles.bioActions}>
                    <CharCounter value={bioDraft.length} max={LIMITS.bioMax} />
                    <div className={styles.bioButtons}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditingBio(false)}
                        disabled={savingBio}
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        loading={savingBio}
                        disabled={bioDraft.length > LIMITS.bioMax}
                        onClick={saveBio}
                      >
                        Save bio
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <p className={u.bio ? styles.bio : styles.bioEmpty}>
                  {u.bio || (isOwn ? 'You haven’t added a bio yet.' : 'No bio yet.')}
                </p>
              )}

              {isOwn && !editingBio && (
                <div className={styles.ownActions}>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setBioDraft(u.bio ?? '')
                      setBioError(null)
                      setEditingBio(true)
                    }}
                  >
                    Edit bio
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                    Switch user
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      logout()
                      toast.info('Signed out.')
                    }}
                  >
                    Sign out
                  </Button>
                </div>
              )}
            </div>
          </header>
        )}
      </StateView>

      <section className={styles.postsSection} aria-label={`Posts by ${username}`}>
        <h2 className={styles.sectionTitle}>Posts</h2>
        <StateView
          status={posts.status}
          data={posts.data}
          error={posts.error}
          onRetry={posts.refetch}
          errorTitle="Couldn’t load posts"
          loading={
            <div className={styles.skeletons}>
              <PostCardSkeleton />
              <PostCardSkeleton />
            </div>
          }
          isEmpty={(list) => list.length === 0}
          empty={<EmptyState title={isOwn ? 'You haven’t posted yet' : 'No posts yet'} />}
        >
          {(list) => <PostList posts={list} onDelete={handleDelete} onUpdated={handleUpdated} />}
        </StateView>
      </section>
    </div>
  )
}
