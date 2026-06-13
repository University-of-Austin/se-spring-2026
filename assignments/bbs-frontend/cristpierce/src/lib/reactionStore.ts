/*
 * Local persistence for the current user's reactions.
 *
 * The A2 API can add/remove a reaction but exposes no GET to read them back,
 * and post objects don't carry reaction data. So the client remembers which
 * kind the active user picked per post in localStorage, keyed by username. This
 * makes "you reacted" survive a refresh. A production backend would expose
 * reaction counts on the post (documented as a known gap in the README).
 */

const key = (username: string) => `bbs:reactions:${username}`

type ReactionMap = Record<string, string>

function read(username: string): ReactionMap {
  try {
    const raw = localStorage.getItem(key(username))
    return raw ? (JSON.parse(raw) as ReactionMap) : {}
  } catch {
    return {}
  }
}

export function getReaction(username: string, postId: number): string | null {
  return read(username)[String(postId)] ?? null
}

export function setReaction(username: string, postId: number, kind: string | null): void {
  try {
    const map = read(username)
    if (kind) map[String(postId)] = kind
    else delete map[String(postId)]
    localStorage.setItem(key(username), JSON.stringify(map))
  } catch {
    /* best-effort persistence */
  }
}
