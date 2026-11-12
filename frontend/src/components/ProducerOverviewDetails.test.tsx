import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ProducerGraphEdge, ProducerGraphNode } from '../api/producerGraph'
import { renderWithProviders } from '../test/render'
import { ProducerOverviewDetails } from './ProducerOverviewDetails'

const producer: ProducerGraphNode = {
  id: 'producer-1',
  type: 'producer',
  label: 'Martin Birch',
  roles: ['producer'],
  attributes: {
    artist_type: 'person',
    album_count: 2,
    band_count: 1,
    betweenness: 0.25,
    community_key: 'community-1',
  },
}

const band: ProducerGraphNode = {
  id: 'band-1',
  type: 'band',
  label: 'Iron Maiden',
  roles: ['band'],
  attributes: { band_type: 'group', album_count: 1 },
}

const album: ProducerGraphNode = {
  id: 'album-1',
  type: 'album',
  label: 'Iron Maiden',
  roles: ['album'],
  attributes: {
    band_id: 'band-1',
    band_name: 'Iron Maiden',
    year: 1980,
    decade: '1980s',
  },
}

const meta = {
  view: 'bands',
  analysis_run_id: 'run-1',
  analysis_version: 'net-test',
  dataset_version: 'mb-test',
  taxonomy_version: '0.2.0',
  graph_version: '0.1.0',
  truncated: false,
  limits: { limit: 100, depth: 1, max_nodes: 500, max_edges: 2000 },
}

function responseFor(nodes: ProducerGraphNode[], truncated = false) {
  return {
    nodes,
    edges: [],
    meta: { ...meta, truncated },
  }
}

function mockFetch(handler: (url: string) => unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url =
        typeof input === 'string'
          ? input
          : input instanceof URL
            ? input.href
            : input.url
      const body = handler(url)
      if (body === undefined) return Promise.reject(new Error(`Unexpected fetch: ${url}`))
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => body,
      })
    }),
  )
}

function renderDetails(
  node: ProducerGraphNode | null,
  incidentProducers: ProducerGraphNode[] = [],
  edge: ProducerGraphEdge | null = null,
) {
  return renderWithProviders(
    <ProducerOverviewDetails
      node={node}
      edge={edge}
      nodes={[producer, band, album]}
      incidentProducers={incidentProducers}
    />,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ProducerOverviewDetails', () => {
  it('shows a producer with its bands and albums from the ego graphs', async () => {
    mockFetch((url) => {
      if (url.includes('/api/v1/producers/producer-1/graph?view=bands')) {
        return responseFor([
          producer,
          band,
          {
            id: 'band-producer',
            type: 'producer',
            label: 'Helloween',
            roles: ['band', 'producer'],
            attributes: {},
          },
        ], true)
      }
      if (url.includes('/api/v1/producers/producer-1/graph?view=albums')) {
        return responseFor([producer, album])
      }
      return undefined
    })

    renderDetails(producer)

    expect(await screen.findByRole('heading', { name: 'Bands' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Albums' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Iron Maiden' })).toHaveAttribute(
      'href',
      '/bands/band-1',
    )
    expect(screen.getByRole('link', { name: 'Helloween' })).toHaveAttribute(
      'href',
      '/bands/band-producer',
    )
    expect(screen.getByRole('link', { name: 'Iron Maiden (1980)' })).toHaveAttribute(
      'href',
      '/albums/album-1',
    )
    expect(screen.getByText(/truncated at its server limit/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open ego graph' })).toHaveAttribute(
      'href',
      '/producers/producer-1/graph',
    )
  })

  it('shows a band with its albums and producer credits', async () => {
    mockFetch((url) => {
      if (url === '/api/v1/bands/band-1') {
        return {
          id: 'band-1',
          mbid: 'mbid-1',
          name: 'Iron Maiden',
          country: 'GB',
          subgenre: 'heavy-metal',
          albums: [
            {
              id: 'album-1',
              mbid: 'mbid-album-1',
              title: 'Iron Maiden',
              year: 1980,
              first_release_date: '1980-04-14',
              credits: [
                {
                  artist_id: 'producer-1',
                  artist_name: 'Martin Birch',
                  role: 'producer',
                  role_name: 'Producer',
                  scope: 'release',
                  supporting_recording_count: 9,
                  recording_count: 9,
                  confidence: 1,
                  status: 'confirmed',
                },
                {
                  artist_id: 'engineer-1',
                  artist_name: 'Engineer',
                  role: 'engineer',
                  role_name: 'Engineer',
                  scope: 'release',
                  supporting_recording_count: 9,
                  recording_count: 9,
                  confidence: 1,
                  status: 'confirmed',
                },
              ],
            },
          ],
        }
      }
      return undefined
    })

    renderDetails(band)

    expect(await screen.findByRole('heading', { name: 'Albums' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Producers' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Iron Maiden (1980)' })).toHaveAttribute(
      'href',
      '/albums/album-1',
    )
    expect(screen.getByRole('link', { name: 'Martin Birch' })).toHaveAttribute(
      'href',
      '/graph?selected=producer-1',
    )
    expect(screen.queryByText('Engineer')).not.toBeInTheDocument()
  })

  it('shows an album with its band, year and all incident producers', () => {
    renderDetails(album, [
      producer,
      {
        ...producer,
        id: 'producer-2',
        label: 'Bob Producer',
      },
    ])

    expect(screen.getByRole('heading', { name: 'Iron Maiden' })).toBeInTheDocument()
    expect(screen.getByText('1980')).toBeInTheDocument()
    expect(screen.getAllByText('Iron Maiden').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Martin Birch' })).toHaveAttribute(
      'href',
      '/graph?selected=producer-1',
    )
    expect(screen.getByRole('link', { name: 'Bob Producer' })).toHaveAttribute(
      'href',
      '/graph?selected=producer-2',
    )
    expect(screen.getByRole('link', { name: 'Open album details' })).toHaveAttribute(
      'href',
      '/albums/album-1',
    )
    expect(screen.getByRole('link', { name: 'Open band details' })).toHaveAttribute(
      'href',
      '/bands/band-1',
    )
  })

  it('shows a panel-local error when related data cannot be loaded', async () => {
    mockFetch(() => undefined)
    renderDetails(producer)
    expect(await screen.findByText('Related relationships are unavailable.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
