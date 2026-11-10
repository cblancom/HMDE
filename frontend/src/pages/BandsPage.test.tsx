import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { BandsPage } from './BandsPage'

const ironMaiden = {
  id: 'band-1',
  mbid: 'mbid-1',
  name: 'Iron Maiden',
  country: 'GB',
  subgenre: 'Heavy Metal',
  album_count: 3,
}

const populatedResponse = {
  items: [ironMaiden],
  total: 1,
  limit: 20,
  offset: 0,
}

const emptyResponse = { items: [], total: 0, limit: 20, offset: 0 }

const taxonomy = {
  version: '0.2.0',
  nodes: [
    { code: 'heavy-metal', name: 'Heavy Metal', parent_code: 'metal', assignable: true },
    { code: 'thrash-metal', name: 'Thrash Metal', parent_code: 'metal', assignable: true },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('BandsPage', () => {
  it('shows a loading state while the request is pending', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    renderWithProviders(<BandsPage />, { route: '/bands' })

    expect(screen.getByRole('status')).toHaveTextContent('Loading bands')
  })

  it('shows an error state and retries the request', async () => {
    let bandCalls = 0
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
      if (url === '/api/v1/taxonomy') {
        return Promise.resolve({ ok: true, status: 200, json: async () => taxonomy })
      }
      bandCalls += 1
      return Promise.resolve(
        bandCalls === 1
          ? { ok: false, status: 500, json: async () => ({}) }
          : { ok: true, status: 200, json: async () => populatedResponse },
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    renderWithProviders(<BandsPage />, { route: '/bands' })

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load bands')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('link', { name: 'Iron Maiden' })).toBeInTheDocument()
  })

  it('renders bands with links to their detail pages', async () => {
    mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/bands': { body: populatedResponse },
    })
    renderWithProviders(<BandsPage />, { route: '/bands' })

    const link = await screen.findByRole('link', { name: 'Iron Maiden' })
    expect(link).toHaveAttribute('href', '/bands/band-1')
    expect(screen.getByRole('cell', { name: 'GB' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Heavy Metal' })).toBeInTheDocument()
    expect(screen.getByText('1 band')).toBeInTheDocument()
  })


  it('updates the decade filter in the URL', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/bands': { body: populatedResponse },
    })
    renderWithProviders(<BandsPage />, { route: '/bands' })

    await screen.findByRole('link', { name: 'Iron Maiden' })
    fireEvent.change(screen.getByLabelText('Decade'), { target: { value: '1980s' } })

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/bands?decade=1980s&limit=20&offset=0',
        expect.anything(),
      )
    })
  })

  it('shows an empty state when no bands match', async () => {
    mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/bands': { body: emptyResponse },
    })
    renderWithProviders(<BandsPage />, { route: '/bands' })

    expect(await screen.findByText('No bands match these filters.')).toBeInTheDocument()
  })

  it('reads filters from the URL', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/bands': { body: populatedResponse },
    })
    renderWithProviders(<BandsPage />, {
      route: '/bands?q=Maiden&subgenre=heavy-metal',
    })

    expect(screen.getByLabelText('Search bands')).toHaveValue('Maiden')
    expect(await screen.findByRole('option', { name: /Heavy Metal/ })).toBeInTheDocument()
    expect(screen.getByLabelText('Subgenre')).toHaveValue('heavy-metal')
    expect(await screen.findByRole('link', { name: 'Iron Maiden' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/bands?q=Maiden&subgenre=heavy-metal&limit=20&offset=0',
      expect.anything(),
    )
  })

  it('updates the search and subgenre filters', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/bands': { body: emptyResponse },
    })
    renderWithProviders(<BandsPage />, { route: '/bands' })

    expect(await screen.findByText('No bands match these filters.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Search bands'), {
      target: { value: 'slayer' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/bands?q=slayer&limit=20&offset=0',
        expect.anything(),
      )
    })

    fireEvent.change(screen.getByLabelText('Subgenre'), {
      target: { value: 'thrash-metal' },
    })

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/bands?q=slayer&subgenre=thrash-metal&limit=20&offset=0',
        expect.anything(),
      )
    })
  })
})
