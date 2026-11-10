import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { AlbumDetailPage } from './AlbumDetailPage'

const album = {
  id: 'album-1',
  mbid: 'mbid-album-1',
  title: 'Iron Maiden',
  band_id: 'band-1',
  band_name: 'Iron Maiden',
  year: 1980,
  first_release_date: '1980-04-14',
  primary_subgenre: 'Heavy Metal',
  secondary_subgenres: ['NWOBHM'],
  credits: [
    {
      artist_id: 'artist-1',
      artist_name: 'Martin Birch',
      role: 'producer',
      role_name: 'Producer',
      scope: 'release_group',
      supporting_recording_count: 9,
      recording_count: 9,
      support_ratio: 1,
      confidence: 1,
      status: 'confirmed',
    },
  ],
}

function renderAlbum(route = '/albums/album-1') {
  return renderWithProviders(
    <Routes>
      <Route path="/albums/:albumId" element={<AlbumDetailPage />} />
    </Routes>,
    { route },
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AlbumDetailPage', () => {
  it('renders band, taxonomy and support-aware credits', async () => {
    mockFetchRoutes({ '/api/v1/albums/album-1': { body: album } })
    renderAlbum()

    expect(await screen.findByRole('heading', { name: 'Iron Maiden', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Iron Maiden' })).toHaveAttribute('href', '/bands/band-1')
    expect(screen.getByText('Also classified as NWOBHM.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Martin Birch' })).toHaveAttribute(
      'href',
      '/producers/artist-1',
    )
    expect(screen.getByRole('cell', { name: 'Full album' })).toBeInTheDocument()
  })

  it('shows loading, error and not-found states', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    renderAlbum()
    expect(screen.getByRole('status')).toHaveTextContent('Loading album')

    vi.unstubAllGlobals()
    mockFetchRoutes({ '/api/v1/albums/missing': { status: 404, body: {} } })
    renderAlbum('/albums/missing')
    expect(await screen.findByText('Album not found.')).toBeInTheDocument()
  })
})
