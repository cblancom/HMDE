import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { ProducersPage } from './ProducersPage'

const producer = {
  id: 'producer-1',
  mbid: 'mbid-producer-1',
  name: 'Martin Birch',
  country: 'GB',
  artist_type: 'person',
  album_count: 17,
  band_count: 5,
  self_produced_albums: 0,
  betweenness: 0.125,
  community_key: 'community-001',
}
const populated = { items: [producer], total: 1, limit: 20, offset: 0 }
const empty = { items: [], total: 0, limit: 20, offset: 0 }
const taxonomy = { version: '0.2.0', nodes: [] }

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ProducersPage', () => {
  it('renders producer rankings and URLs state', async () => {
    mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/producers': { body: populated },
    })
    renderWithProviders(<ProducersPage />, { route: '/producers?sort=band_count&q=birch' })

    expect(screen.getByLabelText('Search producers')).toHaveValue('birch')
    expect(screen.getByLabelText('Rank by')).toHaveValue('band_count')
    expect(await screen.findByRole('link', { name: 'Martin Birch' })).toHaveAttribute(
      'href',
      '/producers/producer-1',
    )
    expect(screen.getByText('1 producer')).toBeInTheDocument()
  })

  it('updates sort and shows empty state', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/taxonomy': { body: taxonomy },
      '/api/v1/producers': { body: empty },
    })
    renderWithProviders(<ProducersPage />, { route: '/producers' })

    expect(await screen.findByText('No producers match these filters.')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Rank by'), { target: { value: 'betweenness' } })
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/producers?sort=betweenness&order=desc&limit=20&offset=0',
        expect.anything(),
      )
    })
  })
})
