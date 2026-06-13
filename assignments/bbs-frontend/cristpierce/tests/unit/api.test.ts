import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_BASE, ApiError, api, normalizeErrorBody } from '../../src/lib/api'

describe('normalizeErrorBody', () => {
  it('uses a string detail directly (HTTPException)', () => {
    expect(normalizeErrorBody(404, { detail: 'User not found' })).toEqual({
      message: 'User not found',
    })
  })

  it('parses a 422 validation array into per-field errors', () => {
    const body = {
      detail: [
        {
          loc: ['body', 'message'],
          msg: 'String should have at least 1 character',
          type: 'string_too_short',
        },
      ],
    }
    const out = normalizeErrorBody(422, body)
    expect(out.message).toMatch(/at least 1 character/)
    expect(out.fieldErrors).toEqual({
      message: 'String should have at least 1 character',
    })
  })

  it('strips Pydantic "Value error," prefixes', () => {
    const body = {
      detail: [
        {
          loc: ['body', 'username'],
          msg: 'Value error, Username must contain only letters, digits, and underscores',
          type: 'value_error',
        },
      ],
    }
    expect(normalizeErrorBody(422, body).fieldErrors).toEqual({
      username: 'Username must contain only letters, digits, and underscores',
    })
  })

  it('falls back to a status default when there is no detail', () => {
    expect(normalizeErrorBody(409, {}).message).toMatch(/already exists/i)
    expect(normalizeErrorBody(500, undefined).message).toMatch(/server/i)
  })
})

describe('api client (fetch mocked)', () => {
  const realFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = realFetch
    vi.restoreAllMocks()
  })

  function mockFetch(impl: (url: string, init: RequestInit) => Promise<Response>) {
    globalThis.fetch = vi.fn(impl as typeof fetch)
  }

  it('injects the X-Username header and JSON body on createPost', async () => {
    const calls: Array<[string, RequestInit]> = []
    mockFetch(async (url, init) => {
      calls.push([String(url), init])
      return new Response(
        JSON.stringify({
          id: 1,
          username: 'alice',
          message: 'hi',
          created_at: '2026-06-08T12:00:00',
          updated_at: null,
        }),
        { status: 201 },
      )
    })

    const post = await api.createPost('alice', 'hi')
    expect(post.id).toBe(1)

    const [url, init] = calls[0]
    expect(url).toBe(`${API_BASE}/posts`)
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['X-Username']).toBe('alice')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
  })

  it('returns undefined for a 204 (delete) without parsing a body', async () => {
    mockFetch(async () => new Response(null, { status: 204 }))
    await expect(api.deletePost(5)).resolves.toBeUndefined()
  })

  it('throws an ApiError carrying the server detail on 404', async () => {
    mockFetch(async () => new Response(JSON.stringify({ detail: 'Post not found' }), { status: 404 }))
    await expect(api.getPost(99)).rejects.toMatchObject({
      status: 404,
      message: 'Post not found',
    })
  })

  it('surfaces 422 field errors so the form can show them inline', async () => {
    mockFetch(
      async () =>
        new Response(
          JSON.stringify({
            detail: [
              {
                loc: ['body', 'message'],
                msg: 'String should have at most 500 characters',
                type: 'string_too_long',
              },
            ],
          }),
          { status: 422 },
        ),
    )
    const err = (await api.createPost('alice', 'x'.repeat(501)).catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(422)
    expect(err.fieldErrors?.message).toMatch(/500/)
  })

  it('wraps a network failure as ApiError(isNetwork) with status 0', async () => {
    mockFetch(async () => {
      throw new TypeError('Failed to fetch')
    })
    const err = (await api.listUsers().catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.isNetwork).toBe(true)
    expect(err.status).toBe(0)
  })

  it('builds GET /posts query strings and omits empty params', async () => {
    let captured = ''
    mockFetch(async (url) => {
      captured = String(url)
      return new Response('[]', { status: 200 })
    })
    await api.listPosts({ q: 'hello', limit: 20, offset: 0, username: '' })
    expect(captured).toContain('q=hello')
    expect(captured).toContain('limit=20')
    expect(captured).toContain('offset=0')
    expect(captured).not.toContain('username=')
  })
})
