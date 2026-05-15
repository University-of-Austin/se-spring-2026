import { ApiError } from '../../api/types'

/**
 * Normalize any thrown thing into a human string for UI display.
 * Split from States.tsx so the component file exports only React
 * components (keeps Fast Refresh happy under react-refresh's
 * only-export-components rule).
 */
export function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  return 'Unknown error.'
}
