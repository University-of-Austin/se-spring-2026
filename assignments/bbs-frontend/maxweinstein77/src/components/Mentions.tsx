// Renders post text with @username substrings turned into <Link>s to that
// user's profile. Pure parser -- doesn't check whether the user exists,
// so clicking a dead mention just lands on the UserProfile 404 view.
//
// Regex notes:
//   (?<![a-zA-Z0-9_])  -- not preceded by a word char, so "foo@alice.com"
//                         doesn't match the @alice piece (it's part of an
//                         email-like string, not a real mention).
//   @                  -- literal @
//   ([a-zA-Z0-9_]{3,20})  -- captured username, same rule as A2
//   (?![a-zA-Z0-9_])    -- not followed by a word char, so a 25-char string
//                         won't get truncated to a fake 20-char mention.

import { Fragment, type ReactNode } from "react";
import { Link } from "react-router-dom";
import styles from "./Mentions.module.css";

const MENTION_RE = /(?<![a-zA-Z0-9_])@([a-zA-Z0-9_]{3,20})(?![a-zA-Z0-9_])/g;

interface Props {
  text: string;
}

export function Mentions({ text }: Props) {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  // Reset state in case the regex was used elsewhere (the /g flag is stateful).
  MENTION_RE.lastIndex = 0;

  while ((match = MENTION_RE.exec(text)) !== null) {
    const before = text.slice(lastIndex, match.index);
    if (before) parts.push(<Fragment key={key++}>{before}</Fragment>);
    const username = match[1];
    parts.push(
      <Link key={key++} to={`/users/${username}`} className={styles.mention}>
        @{username}
      </Link>,
    );
    lastIndex = match.index + match[0].length;
  }

  const after = text.slice(lastIndex);
  if (after) parts.push(<Fragment key={key++}>{after}</Fragment>);

  return <>{parts}</>;
}
