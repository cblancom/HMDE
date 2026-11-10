import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { AlbumsPage } from './AlbumsPage'

const album = {
  id: 'album-1',
  mbid: 'mbid-album-1',
  title: 'Iron Maiden',
  band_id: 'band-1',
  band_name: 'Iron Maiden',
  year: 1980,
  first_release_date: '1980-04-14',
  primary_subgenre: 'Heavy Metal',
  producer_count: 1,
  credit_count: 5,
}

const populated = { items: [album], total: 1, limit: 20, offset: 0 }
const empty = { items: [], total: 0, limit: 20, offset: 0 }
const taxonomy = {
  version: '0.2.0',
  nodes: [{ code: 'heavy-metal', name: 'Heavy Metal', parent_code: null, assignable: true }],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AlbumsPage', () => {
  it('renders albums with band links and filters', async () => {
    mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/albums': { body: populated },
    })
    renderWithProviders(<AlbumsPage />, { route: '/albums?q=iron&decade=1980s' })

    expect(screen.getByLabelText('Search albums')).toHaveValue('iron')
    expect(screen.getByLabelText('Decade')).toHaveValue('1980s')
    const links = await screen.findAllByRole('link', { name: 'Iron Maiden' })
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      '/albums/album-1',
      '/bands/band-1',
    ])
    expect(screen.getByText('1 album')).toBeInTheDocument()
  })

  it('shows empty and error states', async () => {
    mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/albums': { body: empty },
    })
    renderWithProviders(<AlbumsPage />, { route: '/albums' })
    expect(await screen.findByText('No albums match these filters.')).toBeInTheDocument()

    vi.unstubAllGlobals()
    mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/albums': { status: 500, body: {} },
    })
    renderWithProviders(<AlbumsPage />, { route: '/albums' })
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load albums')
  })

  it('submits a new album search', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/albums': { body: empty },
    })
    renderWithProviders(<AlbumsPage />, { route: '/albums' })

    fireEvent.change(screen.getByLabelText('Search albums'), { target: { value: 'killers' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/albums?q=killers&limit=20&offset=0',
        expect.anything(),
      )
    })
  })
})
