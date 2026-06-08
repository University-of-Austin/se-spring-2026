/*
 * @mention linkification. Turns "hey @alice" into text plus a <Link> to that
 * user's profile, without trusting the message as HTML (we only ever build
 * React nodes from plain substrings, so there is no XSS surface).
 *
 * A token only counts as a mention when the '@' is at a word boundary, so
 * "email@host" is left as plain text.
 */

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { LIMITS } from './types'

const MENTION_RE = new RegExp(`@([a-zA-Z0-9_]{1,${LIMITS.usernameMax}})`, 'g')
const WORD_CHAR = /[a-zA-Z0-9_]/

export function renderMessage(message: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let lastIndex = 0
  let key = 0
  let match: RegExpExecArray | null

  MENTION_RE.lastIndex = 0
  while ((match = MENTION_RE.exec(message)) !== null) {
    const start = match.index
    const prev = start > 0 ? message[start - 1] : ''
    // Require a boundary before '@' so we don't linkify mid-word (e.g. emails).
    if (prev && WORD_CHAR.test(prev)) continue

    if (start > lastIndex) nodes.push(message.slice(lastIndex, start))

    const name = match[1]
    nodes.push(
      <Link key={`m${key++}`} to={`/users/${name}`} className="mention">
        @{name}
      </Link>,
    )
    lastIndex = start + match[0].length
  }

  if (lastIndex < message.length) nodes.push(message.slice(lastIndex))
  return nodes
}
