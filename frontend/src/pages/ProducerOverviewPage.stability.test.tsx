import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes, useLocation } from 'react-router'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { ProducerOverviewPage } from './ProducerOverviewPage'

const captured = vi.hoisted(() => ({ graphs: [] as unknown[] }))

vi.mock('../components/ProducerGraph', () => ({
  ProducerGraph: ({
    graph,
    onSelect,
  }: {
    graph: unknown
    onSelect?: (id: string, kind: 'node' | 'edge') => void
  }) => {
    captured.graphs.push(graph)
    return (
      <button type="button" onClick={() => onSelect?.('producer-1', 'node')}>
        Select node
      </button>
    )
  },
}))

const meta = {
  scope: 'overview',
  view: 'bands',
  analysis_run_id: 'run-1',
  analysis_version: 'net-test',
  dataset_version: 'mb-test',
  taxonomy_version: '0.2.0',
  graph_version: '0.1.0',
  truncated: false,
  matched_producers: 1,
  selected_producers: 1,
  returned_bands: 1,
  returned_albums: 0,
  omitted_bands: 0,
  omitted_albums: 0,
  include_isolated: false,
  limits: {
    producer_limit: 0,
    band_limit: 0,
    album_limit: 500,
    max_nodes: 5000,
    max_edges: 5000,
  },
}

const overview = {
  nodes: [
    {
      id: 'producer-1',
      type: 'producer',
      label: 'Alice Producer',
      roles: ['producer'],
      attributes: { artist_type: 'person', album_count: 1, band_count: 1 },
    },
    {
      id: 'band-1',
      type: 'band',
      label: 'Shared Band',
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
      weight: 1,
      support_ratio: null,
      supporting_recordings: null,
      album_recordings: null,
      album_count: 1,
      evidence: {},
    },
  ],
  meta,
}

const producerGraph = {
  nodes: [overview.nodes[0]],
  edges: [],
  meta: {
    view: 'bands',
    analysis_run_id: 'run-1',
    analysis_version: 'net-test',
    dataset_version: 'mb-test',
    taxonomy_version: '0.2.0',
    graph_version: '0.1.0',
    truncated: false,
    returned_neighbors: 0,
    omitted_neighbors: 0,
    limits: { limit: 20, depth: 1, max_nodes: 500, max_edges: 2000 },
  },
}

const bands = {
  items: [
    {
      id: 'band-1',
      mbid: 'mbid-1',
      name: 'Shared Band',
      country: 'GB',
      subgenre: 'heavy-metal',
      album_count: 1,
    },
  ],
  total: 1,
  limit: 200,
  offset: 0,
}

function LocationProbe() {
  const location = useLocation()
  return <p data-testid="location">{location.search}</p>
}

function renderOverview() {
  return renderWithProviders(
    <Routes>
      <Route
        path="/graph"
        element={
          <>
            <ProducerOverviewPage />
            <LocationProbe />
          </>
        }
      />
    </Routes>,
    { route: '/graph' },
  )
}

afterEach(() => {
  captured.graphs = []
  vi.unstubAllGlobals()
})

describe('ProducerOverviewPage stability', () => {
  it('does not rebuild the adapted graph when a node is selected', async () => {
    mockFetchRoutes({
      '/api/v1/taxonomy': { body: { version: '0.2.0', nodes: [] } },
      '/api/v1/bands': { body: bands },
      '/api/v1/producers/producer-1/graph': { body: producerGraph },
      '/api/v1/graph/producers': { body: overview },
    })
    renderOverview()

    await screen.findByRole('heading', { name: 'Producer network' })
    expect(captured.graphs.length).toBeGreaterThan(0)
    const initialGraph = captured.graphs[0]

    fireEvent.click(screen.getByRole('button', { name: 'Select node' }))
    await waitFor(() => {
      expect(screen.getByTestId('location').textContent).toContain('selected=producer-1')
    })
    expect(captured.graphs.at(-1)).toBe(initialGraph)
  })
})
