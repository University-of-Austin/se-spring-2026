// Inline error box. Extracts ApiError.detail if available, else falls back to
// the standard Error.message. role="alert" tells screen readers to announce it.

import { ApiError } from '../api/client'

export function ErrorMessage({ error }: { error: Error }) {
  const message = error instanceof ApiError ? error.detail : error.message
  return (
    <div
      role="alert"
      className="rounded border border-error bg-error/10 px-3 py-2 text-sm text-error"
    >
      {message}
    </div>
  )
}
