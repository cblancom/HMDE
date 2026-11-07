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
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({}),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => populatedResponse,
      })
    vi.stubGlobal('fetch', fetchMock)

    renderWithProviders(<BandsPage />, { route: '/bands' })

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load bands')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('link', { name: 'Iron Maiden' })).toBeInTheDocument()
  })

  it('renders bands with links to their detail pages', async () => {
    mockFetchRoutes({ '/api/v1/bands': { body: populatedResponse } })
    renderWithProviders(<BandsPage />, { route: '/bands' })

    const link = await screen.findByRole('link', { name: 'Iron Maiden' })
    expect(link).toHaveAttribute('href', '/bands/band-1')
    expect(screen.getByRole('cell', { name: 'GB' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Heavy Metal' })).toBeInTheDocument()
    expect(screen.getByText('1 band')).toBeInTheDocument()
  })

  it('shows an empty state when no bands match', async () => {
    mockFetchRoutes({ '/api/v1/bands': { body: emptyResponse } })
    renderWithProviders(<BandsPage />, { route: '/bands' })

    expect(await screen.findByText('No bands match these filters.')).toBeInTheDocument()
  })

  it('reads filters from the URL', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/bands': { body: populatedResponse },
    })
    renderWithProviders(<BandsPage />, {
      route: '/bands?q=Maiden&subgenre=heavy-metal',
    })

    expect(screen.getByLabelText('Search bands')).toHaveValue('Maiden')
    expect(screen.getByLabelText('Subgenre')).toHaveValue('heavy-metal')
    expect(await screen.findByRole('link', { name: 'Iron Maiden' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/bands?q=Maiden&subgenre=heavy-metal',
      expect.anything(),
    )
  })

  it('updates the search and subgenre filters', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/bands': { body: emptyResponse },
    })
    renderWithProviders(<BandsPage />, { route: '/bands' })

    expect(await screen.findByText('No bands match these filters.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Search bands'), {
      target: { value: 'slayer' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/bands?q=slayer', expect.anything())
    })

    fireEvent.change(screen.getByLabelText('Subgenre'), {
      target: { value: 'thrash-metal' },
    })

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/bands?q=slayer&subgenre=thrash-metal',
        expect.anything(),
      )
    })
  })
})
