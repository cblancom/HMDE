import { fireEvent, screen, waitFor } from '@testing-library/react'
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

function renderOverview(route = '/graph') {
  return renderWithProviders(
    <Routes><Route path="/graph" element={<ProducerOverviewPage />} /></Routes>,
    { route },
  )
}

function mockOverview(body: unknown = overview, status = 200) {
  return mockFetchRoutes({
    '/api/v1/taxonomy': { body: taxonomy },
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
    expect(screen.getByText('Carol Isolated')).toBeInTheDocument()
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

    expect(screen.getByText('Carol Isolated')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Show isolated producers'))
    expect(screen.queryByText('Carol Isolated')).not.toBeInTheDocument()
    expect(screen.getByText(/1 isolated producer hidden/)).toBeInTheDocument()
  })

  it('shows connected producers for a shared node and producer drill-down links', async () => {
    mockOverview()
    const { unmount } = renderOverview('/graph?selected=band-1')

    expect(await screen.findByRole('heading', { name: 'Shared Band' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Connected producers' })).toBeInTheDocument()
    const alice = screen.getByRole('link', { name: 'Alice Producer' })
    expect(alice).toHaveAttribute('href', '/graph?selected=producer-1')
    expect(screen.getAllByRole('link', { name: 'Ego graph' })).toHaveLength(2)

    unmount()
    renderOverview('/graph?selected=producer-1')
    expect(await screen.findByRole('link', { name: 'Open ego graph' })).toHaveAttribute(
      'href',
      '/producers/producer-1/graph',
    )
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
