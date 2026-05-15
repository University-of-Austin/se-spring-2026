import { z } from 'zod'

/**
 * Client-side mirrors of A2's server constraints.
 * Server is still the source of truth — these just save a round-trip.
 */

export const USERNAME_REGEX = /^[a-zA-Z0-9_]+$/
export const USERNAME_MIN = 3
export const USERNAME_MAX = 20
export const MESSAGE_MIN = 1
export const MESSAGE_MAX = 500
export const BIO_MAX = 200

export const usernameSchema = z
  .string()
  .min(USERNAME_MIN, `Username must be at least ${USERNAME_MIN} characters.`)
  .max(USERNAME_MAX, `Username can be at most ${USERNAME_MAX} characters.`)
  .regex(USERNAME_REGEX, 'Letters, digits, and underscores only.')

export const messageSchema = z
  .string()
  .min(MESSAGE_MIN, 'Cannot post an empty message.')
  .max(MESSAGE_MAX, `Messages are capped at ${MESSAGE_MAX} characters.`)

export const bioSchema = z
  .string()
  .max(BIO_MAX, `Bio is capped at ${BIO_MAX} characters.`)

export function isValidUsername(s: string): boolean {
  return usernameSchema.safeParse(s).success
}

export function isValidMessage(s: string): boolean {
  return messageSchema.safeParse(s).success
}
