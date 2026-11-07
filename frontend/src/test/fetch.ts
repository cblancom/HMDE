import { vi } from 'vitest'

type MockResponse = {
  status?: number
  body: unknown
}

export function mockFetchRoutes(routes: Record<string, MockResponse>) {
  const entries = Object.entries(routes).sort(([left], [right]) => right.length - left.length)
  const mock = vi.fn((input: RequestInfo | URL) => {
    const url =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.href
          : input.url
    const match = entries.find(
      ([prefix]) => url === prefix || url.startsWith(`${prefix}?`),
    )

    if (!match) {
      return Promise.reject(new Error(`Unexpected fetch: ${url}`))
    }

    const [, response] = match
    const status = response.status ?? 200

    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: async () => response.body,
    })
  })

  vi.stubGlobal('fetch', mock)
  return mock
}
