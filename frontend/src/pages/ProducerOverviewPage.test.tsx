import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { ProducerOverviewPage } from './ProducerOverviewPage'

const meta = {
  scope: 'overview',
  view: 'bands',
  analysis_run_id: 'run-1',
  analysis_version: 'net-test',
  dataset_version: 'mb-test',
  taxonomy_version: '0.2.0',
  graph_version: '0.1.0',
  truncated: false,
  matched_producers: 3,
  selected_producers: 3,
  include_isolated: true,
  limits: { producer_limit: 0, max_nodes: 1000, max_edges: 2000 },
}

const overview = {
  nodes: [
    {
      id: 'producer-1',
      type: 'producer',
      label: 'Alice Producer',
      roles: ['producer'],
      attributes: { artist_type: 'person', album_count: 2, band_count: 2, betweenness: 0.5 },
    },
    {
      id: 'producer-2',
      type: 'producer',
      label: 'Bob Producer',
      roles: ['producer'],
      attributes: { artist_type: 'person', album_count: 1, band_count: 1, betweenness: 0.2 },
    },
    {
      id: 'producer-3',
      type: 'producer',
      label: 'Carol Isolated',
      roles: ['producer'],
      attributes: { artist_type: 'person', album_count: 1, band_count: 0, betweenness: null },
    },
    {
      id: 'band-1',
      type: 'band',
      label: 'Shared Band',
      roles: ['band'],
      attributes: { band_type: 'group' },
    },
    {
      id: 'band-2',
      type: 'band',
      label: 'Other Band',
      roles: ['band'],
      attributes: { band_type: 'group' },
    },
  ],
  edges: [
    {
      source: 'producer-1',
      target: 'band-1',
      layer: 'producer_band',
      role: 'producer',
      weight: 2,
      support_ratio: null,
      supporting_recordings: null,
      album_recordings: null,
      album_count: 2,
      evidence: { role_mix: { producer: 2 } },
    },
    {
      source: 'producer-2',
      target: 'band-1',
      layer: 'producer_band',
      role: 'co-producer',
      weight: 1,
      support_ratio: null,
      supporting_recordings: null,
      album_recordings: null,
      album_count: 1,
      evidence: { role_mix: { 'co-producer': 1 } },
    },
    {
      source: 'producer-1',
      target: 'band-2',
      layer: 'producer_band',
      role: 'producer',
      weight: 1,
      support_ratio: null,
      supporting_recordings: null,
      album_recordings: null,
      album_count: 1,
      evidence: { role_mix: { producer: 1 } },
    },
  ],
  meta,
}

const taxonomy = { version: '0.2.0', nodes: [] }
const overviewWithLayout = {
  ...overview,
  layout: {
    algorithm: 'bipartite' as const,
    nodes: overview.nodes.map((node, index) => ({
      id: node.id,
      x: node.type === 'producer' ? 100 : 900,
      y: 100 + index * 60,
    })),
  },
}
const producerGraph = {
  nodes: [
    overview.nodes[0],
    overview.nodes[3],
    {
      id: 'album-1',
      type: 'album',
      label: 'Shared Album',
      roles: ['album'],
      attributes: { band_id: 'band-1', band_name: 'Shared Band', year: 1991 },
    },
  ],
  edges: [],
  meta: {
    view: 'bands',
    analysis_run_id: 'run-1',
    analysis_version: 'net-test',
    dataset_version: 'mb-test',
    taxonomy_version: '0.2.0',
    graph_version: '0.1.0',
    truncated: false,
    limits: { limit: 100, depth: 1, max_nodes: 500, max_edges: 2000 },
  },
}
const bandDetail = {
  id: 'band-1',
  mbid: 'mbid-1',
  name: 'Shared Band',
  country: 'GB',
  subgenre: 'heavy-metal',
  albums: [
    {
      id: 'album-1',
      mbid: 'mbid-album-1',
      title: 'Shared Album',
      year: 1991,
      first_release_date: '1991-01-01',
      credits: [
        {
          artist_id: 'producer-1',
          artist_name: 'Alice Producer',
          role: 'producer',
          role_name: 'Producer',
          scope: 'release',
          supporting_recording_count: 8,
          recording_count: 8,
          confidence: 1,
          status: 'confirmed',
        },
        {
          artist_id: 'producer-2',
          artist_name: 'Bob Producer',
          role: 'co-producer',
          role_name: 'Co-producer',
          scope: 'release',
          supporting_recording_count: 4,
          recording_count: 8,
          confidence: 1,
          status: 'confirmed',
        },
      ],
    },
  ],
}
const bands = {
  items: [
    { id: 'band-1', mbid: 'mbid-1', name: 'Shared Band', country: 'GB', subgenre: 'heavy-metal', album_count: 5 },
    { id: 'band-2', mbid: 'mbid-2', name: 'Other Band', country: 'US', subgenre: 'thrash-metal', album_count: 2 },
  ],
  total: 2,
  limit: 200,
  offset: 0,
}

function renderOverview(route = '/graph') {
  return renderWithProviders(
    <Routes><Route path="/graph" element={<ProducerOverviewPage />} /></Routes>,
    { route },
  )
}

function mockOverview(body: unknown = overview, status = 200) {
  return mockFetchRoutes({
    '/api/v1/taxonomy': { body: taxonomy },
    '/api/v1/bands': { body: bands },
    '/api/v1/bands/band-1': { body: bandDetail },
    '/api/v1/producers/producer-1/graph': { body: producerGraph },
    '/api/v1/graph/producers': { body, status },
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('ProducerOverviewPage', () => {
  it('renders the global overview with counts, legend and tables', async () => {
    mockOverview()
    renderOverview()

    expect(await screen.findByRole('heading', { name: 'Producer network' })).toBeInTheDocument()
    expect(screen.getByTestId('producer-graph')).toBeInTheDocument()
    expect(screen.getByText(/5 nodes/)).toBeInTheDocument()
    expect(screen.getByText(/3 edges/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'How to read the network' })).toBeInTheDocument()
    expect(screen.getByText('View the network as tables')).toBeInTheDocument()
    expect(screen.getAllByText('Carol Isolated').length).toBeGreaterThan(0)

    const index = screen.getByRole('complementary', { name: 'Network index' })
    expect(within(index).getByText('Producers')).toBeInTheDocument()
    expect(within(index).getByText('Bands')).toBeInTheDocument()
    fireEvent.click(within(index).getByText('Bands'))
    expect(within(index).getByRole('link', { name: 'Shared Band' })).toHaveAttribute(
      'href',
      '/bands/band-1',
    )
    expect(screen.queryByText('1960 to 2026')).not.toBeInTheDocument()
  })

  it('requests bands with the active server filters', async () => {
    const fetchMock = mockOverview()
    renderOverview('/graph?decade=1990s&subgenre=heavy-metal')

    await screen.findByRole('heading', { name: 'Producer network' })
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/bands?subgenre=heavy-metal&decade=1990s&limit=200',
        expect.anything(),
      )
    })
  })

  it('updates server parameters and keeps the URL state', async () => {
    const fetchMock = mockOverview()
    renderOverview()

    await screen.findByRole('heading', { name: 'Producer network' })
    fireEvent.change(screen.getByLabelText('Producers'), { target: { value: '10' } })
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('producer_limit=10'),
        expect.anything(),
      )
    })
    expect(await screen.findByLabelText('Producers')).toHaveValue('10')
  })

  it('hides isolated producers immediately and updates counts', async () => {
    mockOverview()
    renderOverview()
    await screen.findByRole('heading', { name: 'Producer network' })

    const table = screen.getByText('View the network as tables').closest('details')
    expect(table).not.toBeNull()
    expect(within(table as HTMLElement).getByText('Carol Isolated')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Show isolated producers'))
    expect(within(table as HTMLElement).queryByText('Carol Isolated')).not.toBeInTheDocument()
    expect(screen.getByText(/1 isolated producer hidden/)).toBeInTheDocument()
  })

  it('shows connected producers for a shared node and producer drill-down links', async () => {
    mockOverview()
    const { unmount } = renderOverview('/graph?selected=band-1')

    expect(await screen.findByRole('heading', { name: 'Shared Band' })).toBeInTheDocument()
    const details = screen.getByRole('complementary', { name: 'Graph details' })
    expect(await within(details).findByRole('heading', { name: 'Producers' })).toBeInTheDocument()
    const alice = within(details).getByRole('link', { name: 'Alice Producer' })
    expect(alice).toHaveAttribute('href', '/graph?selected=producer-1')
    expect(within(details).getByRole('link', { name: 'Shared Album (1991)' })).toHaveAttribute(
      'href',
      '/albums/album-1',
    )

    unmount()
    renderOverview('/graph?selected=producer-1')
    expect(await screen.findByRole('link', { name: 'Open ego graph' })).toHaveAttribute(
      'href',
      '/producers/producer-1/graph',
    )
  })

  it('toggles the index and details panels independently', async () => {
    mockOverview()
    renderOverview()
    await screen.findByRole('heading', { name: 'Producer network' })

    expect(screen.getByRole('complementary', { name: 'Network index' })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: 'Graph details' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Index' }))
    expect(screen.queryByRole('complementary', { name: 'Network index' })).not.toBeInTheDocument()
    expect(screen.getByTestId('producer-graph')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Index' }))
    expect(screen.getByRole('complementary', { name: 'Network index' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Details' }))
    expect(screen.queryByRole('complementary', { name: 'Graph details' })).not.toBeInTheDocument()
    expect(screen.getByTestId('producer-graph')).toBeInTheDocument()
  })

  it('requests the selected layout and falls back when coordinates are missing', async () => {
    const fetchMock = mockOverview()
    renderOverview()
    await screen.findByRole('heading', { name: 'Producer network' })

    fireEvent.change(screen.getByLabelText('Layout'), { target: { value: 'bipartite' } })
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('layout=bipartite'),
        expect.anything(),
      )
    })
    expect(
      await screen.findByText(/The requested layout is unavailable/),
    ).toBeInTheDocument()
  })

  it('applies a static layout and disables the physics controls', async () => {
    mockOverview(overviewWithLayout)
    renderOverview('/graph?layout=bipartite')

    expect(await screen.findByRole('heading', { name: 'Producer network' })).toBeInTheDocument()
    expect(screen.getByLabelText('Layout')).toHaveValue('bipartite')
    expect(screen.getByText(/Static layout/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Freeze layout' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Resume physics' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reheat' })).toBeDisabled()
  })

  it('explains a selected entity that is not in the current view', async () => {
    mockOverview()
    renderOverview('/graph?selected=missing')

    expect(
      await screen.findByText(/The selected entity is not in the current view/),
    ).toBeInTheDocument()
  })

  it('shows truncation and invalid-view notices', async () => {
    mockOverview({ ...overview, meta: { ...meta, truncated: true } })
    renderOverview('/graph?view=unknown')

    expect(await screen.findByText(/truncated at the server limits/)).toBeInTheDocument()
    expect(screen.getByText(/Unknown graph view/)).toBeInTheDocument()
  })

  it('shows empty and error states', async () => {
    mockOverview({ ...overview, nodes: [], edges: [] })
    const { unmount } = renderOverview()
    expect(await screen.findByText('No producers match these filters.')).toBeInTheDocument()

    unmount()
    mockOverview({}, 500)
    renderOverview()
    expect(await screen.findByText('Could not load the producer overview.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
