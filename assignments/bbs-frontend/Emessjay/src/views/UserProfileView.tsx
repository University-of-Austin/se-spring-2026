// User profile = the user record + their posts.  Two hooks; each one
// is wrapped in its own <Loadable> so they can render independently —
// if posts are slow, we still show the name first.

import { useUser, useUserPosts } from "../hooks/useUser";
import { Loadable } from "../components/Loadable";
import { PostRow } from "../components/PostRow";
import { Timestamp } from "../components/Timestamp";
import { NotFoundView } from "../components/NotFoundView";
import styles from "./UserProfileView.module.css";

export function UserProfileView({ username }: { username: string }) {
  const userState = useUser(username);
  const postsState = useUserPosts(username);

  return (
    <div className={styles.wrap}>
      <Loadable state={userState} notFoundView={<NotFoundView what={`User @${username}`} />}>
        {(user) => (
          <header className={styles.header}>
            <h2 className={styles.name}>@{user.username}</h2>
            {user.bio && <p className={styles.bio}>{user.bio}</p>}
            <p className={styles.meta}>
              {user.post_count} {user.post_count === 1 ? "post" : "posts"}
              {" · joined "}
              <Timestamp iso={user.created_at} />
            </p>
          </header>
        )}
      </Loadable>

      <section aria-label={`Posts by @${username}`}>
        <h3 className={styles.postsTitle}>Posts</h3>
        <Loadable
          state={postsState}
          emptyMessage={`@${username} hasn't posted yet.`}
          notFoundView={null}
        >
          {(posts) => (
            <div className={styles.posts}>
              {posts.map((p) => (
                <PostRow key={p.id} post={p} />
              ))}
            </div>
          )}
        </Loadable>
      </section>
    </div>
  );
}
