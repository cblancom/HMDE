import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { mockFetchRoutes } from './test/fetch'
import { renderWithProviders } from './test/render'

const band = {
  id: 'band-1',
  mbid: 'mbid-1',
  name: 'Iron Maiden',
  country: 'GB',
  subgenre: 'Heavy Metal',
  album_count: 3,
}

function mockAppRoutes() {
  return mockFetchRoutes({
    '/health': { body: { status: 'ok', database: 'ok' } },
    '/api/v1/bands': {
      body: { items: [band], total: 1, limit: 20, offset: 0 },
    },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('redirects the root route to the band list', async () => {
    mockAppRoutes()
    renderWithProviders(<App />, { route: '/' })

    expect(await screen.findByRole('heading', { name: 'Bands' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Iron Maiden' })).toBeInTheDocument()
  })

  it('renders the band detail route', async () => {
    mockFetchRoutes({
      '/health': { body: { status: 'ok', database: 'ok' } },
      '/api/v1/bands/band-1': {
        body: { ...band, albums: [] },
      },
      '/api/v1/bands/band-1/graph': {
        body: {
          nodes: [{ id: 'band-1', label: 'Iron Maiden', type: 'band' }],
          edges: [],
          meta: { fixture_version: 'e2-v0.1.0' },
        },
      },
    })
    renderWithProviders(<App />, { route: '/bands/band-1' })

    expect(
      await screen.findByRole('heading', { name: 'Iron Maiden', level: 1 }),
    ).toBeInTheDocument()
  })

  it('renders a not-found page for unknown routes', () => {
    mockFetchRoutes({
      '/health': { body: { status: 'ok', database: 'ok' } },
    })
    renderWithProviders(<App />, { route: '/unknown' })

    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
