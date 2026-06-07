import { request } from './client';
import type { Post, PostsPage, User } from './types';

export { ApiError } from './client';
export type { Post, PostsPage, User } from './types';

// Users -----------------------------------------------------------------

export function listUsers(signal?: AbortSignal): Promise<User[]> {
  return request<User[]>('/users', { signal });
}

export function getUser(username: string, signal?: AbortSignal): Promise<User> {
  return request<User>(`/users/${encodeURIComponent(username)}`, { signal });
}

export function createUser(username: string, bio = ''): Promise<User> {
  return request<User>('/users', { method: 'POST', body: { username, bio } });
}

export function listUserPosts(username: string, signal?: AbortSignal): Promise<Post[]> {
  return request<Post[]>(`/users/${encodeURIComponent(username)}/posts`, { signal });
}

// Posts -----------------------------------------------------------------

export interface ListPostsArgs {
  q?: string;
  username?: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

// Uses offset pagination (A2 supports both offset and cursor; offset is
// simpler for a "load more" UI and avoids dragging cursor-encoding logic into
// the frontend). The PostsPage envelope is synthesized client-side: more pages
// exist iff the server returned a full page.
export async function listPosts({
  q,
  username,
  limit = 20,
  offset = 0,
  signal,
}: ListPostsArgs = {}): Promise<PostsPage> {
  const data = await request<Post[]>('/posts', {
    query: { q, username, limit, offset },
    signal,
  });
  const nextOffset = data.length === limit ? offset + limit : null;
  return { posts: data, nextCursor: nextOffset === null ? null : String(nextOffset) };
}

export function getPost(id: number, signal?: AbortSignal): Promise<Post> {
  return request<Post>(`/posts/${id}`, { signal });
}

export function createPost(username: string, message: string): Promise<Post> {
  return request<Post>('/posts', { method: 'POST', body: { message }, username });
}

export function deletePost(id: number): Promise<void> {
  return request<void>(`/posts/${id}`, { method: 'DELETE' });
}
