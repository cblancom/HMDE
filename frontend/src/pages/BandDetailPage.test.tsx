import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { BandDetailPage } from './BandDetailPage'

const graph = {
  nodes: [
    { id: 'band-1', label: 'Iron Maiden', type: 'band' },
    { id: 'artist-1', label: 'Martin Birch', type: 'producer' },
  ],
  edges: [
    {
      source: 'band-1',
      target: 'artist-1',
      type: 'produced',
      role: 'producer',
      album_count: 1,
      albums: ['Iron Maiden'],
    },
  ],
  meta: { fixture_version: 'e2-v0.1.0' },
}

const detail = {
  id: 'band-1',
  mbid: 'mbid-band-1',
  name: 'Iron Maiden',
  country: 'GB',
  subgenre: 'Heavy Metal',
  albums: [
    {
      id: 'album-1',
      mbid: 'mbid-album-1',
      title: 'Iron Maiden',
      year: 1980,
      first_release_date: '1980-04-14',
      credits: [
        {
          artist_id: 'artist-1',
          artist_name: 'Martin Birch',
          role: 'producer',
          role_name: 'Producer',
          scope: 'recording',
          supporting_recording_count: 9,
          recording_count: 9,
          confidence: 1.0,
          status: 'confirmed',
        },
        {
          artist_id: 'artist-2',
          artist_name: 'Will Malone',
          role: 'producer',
          role_name: 'Producer',
          scope: 'release',
          supporting_recording_count: 9,
          recording_count: 9,
          confidence: 0.8,
          status: 'provisional',
        },
      ],
    },
    {
      id: 'album-2',
      mbid: 'mbid-album-2',
      title: 'Killers',
      year: 1981,
      first_release_date: '1981-02-02',
      credits: [],
    },
  ],
}

function renderDetail(route = '/bands/band-1') {
  return renderWithProviders(
    <Routes>
      <Route path="/bands/:bandId" element={<BandDetailPage />} />
    </Routes>,
    { route },
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('BandDetailPage', () => {
  it('shows a loading state', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    renderDetail()

    expect(screen.getByRole('status')).toHaveTextContent('Loading band')
  })

  it('renders metadata, albums and credits', async () => {
    mockFetchRoutes({
      '/api/v1/bands/band-1': { body: detail },
      '/api/v1/bands/band-1/graph': { body: graph },
    })
    renderDetail()

    expect(
      await screen.findByRole('heading', { name: 'Iron Maiden', level: 1 }),
    ).toBeInTheDocument()
    expect(screen.getByText('Heavy Metal')).toBeInTheDocument()
    expect(screen.getByText('GB')).toBeInTheDocument()
    expect(screen.getByText('mbid-band-1')).toBeInTheDocument()

    const albumHeadings = screen
      .getAllByRole('heading', { level: 3 })
      .map((heading) => heading.textContent)
    expect(albumHeadings).toEqual(['Iron Maiden', 'Killers'])

    expect(screen.getAllByRole('cell', { name: 'Producer' })).toHaveLength(2)
    expect(screen.getByRole('cell', { name: 'Recording' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Release' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '9 of 9 recordings' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Full album' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Confirmed' })).toBeInTheDocument()
    expect(
      screen.getByText(/No documented credits for this album/),
    ).toBeInTheDocument()
  })


  it('links albums and producer credits to their detail pages', async () => {
    mockFetchRoutes({
      '/api/v1/bands/band-1': { body: detail },
      '/api/v1/bands/band-1/graph': { body: graph },
    })
    renderDetail()

    expect(await screen.findByRole('link', { name: 'Iron Maiden' })).toHaveAttribute(
      'href',
      '/albums/album-1',
    )
    expect(await screen.findByRole('link', { name: 'Martin Birch' })).toHaveAttribute(
      'href',
      '/producers/artist-1',
    )
  })

  it('shows an empty state when a band has no albums', async () => {
    mockFetchRoutes({
      '/api/v1/bands/band-1': { body: { ...detail, albums: [] } },
      '/api/v1/bands/band-1/graph': { body: graph },
    })
    renderDetail()

    expect(await screen.findByText('No documented albums for this band.')).toBeInTheDocument()
  })

  it('shows a not-found state for an unknown band', async () => {
    mockFetchRoutes({
      '/api/v1/bands/missing': { status: 404, body: { detail: 'Band not found' } },
    })
    renderDetail('/bands/missing')

    expect(await screen.findByText('Band not found.')).toBeInTheDocument()
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
        json: async () => detail,
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => graph,
      })
    vi.stubGlobal('fetch', fetchMock)

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load this band')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(
      await screen.findByRole('heading', { name: 'Iron Maiden', level: 1 }),
    ).toBeInTheDocument()
  })
})
