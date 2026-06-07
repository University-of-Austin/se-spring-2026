// Centralized URL builders.  Every navigation call goes through here,
// so a route rename is a one-place change and TypeScript catches every
// caller that needs to pass the new params.
//
// encodeURIComponent on username matters: usernames in A2 are
// restricted to [a-zA-Z0-9_]+ so they don't actually need encoding,
// but encoding anyway means a future relaxation of that rule doesn't
// silently break links.

export const paths = {
  feed: () => "/",
  compose: () => "/compose",
  users: () => "/users",
  user: (username: string) => `/users/${encodeURIComponent(username)}`,
  post: (id: number) => `/posts/${id}`,
  identity: () => "/identity",
} as const;
