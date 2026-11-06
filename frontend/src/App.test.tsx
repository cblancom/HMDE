import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

function mockFetchResponse(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders the project name and construction message', () => {
    mockFetchResponse(200, { status: 'ok', database: 'ok' })
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Heavy Metal Data Explorer' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/foundations are under construction/i)).toBeInTheDocument()
  })

  it('shows the loading state while the health request is pending', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))
    render(<App />)

    expect(screen.getByRole('status')).toHaveTextContent('Checking API status')
  })

  it('shows the available state when the API is healthy', async () => {
    mockFetchResponse(200, { status: 'ok', database: 'ok' })
    render(<App />)

    expect(await screen.findByRole('status')).toHaveTextContent('API available')
  })

  it('shows the degraded state when the API reports a database problem', async () => {
    mockFetchResponse(503, { status: 'degraded', database: 'unavailable' })
    render(<App />)

    expect(await screen.findByRole('status')).toHaveTextContent('API degraded')
  })

  it('shows the unavailable state when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    render(<App />)

    expect(await screen.findByRole('status')).toHaveTextContent('API unavailable')
  })
})
