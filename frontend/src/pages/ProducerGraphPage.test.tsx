import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { ProducerGraphPage } from './ProducerGraphPage'

const graph = {
  nodes: [
    { id: 'producer-1', type: 'producer', label: 'Martin Birch', roles: ['producer'], attributes: { artist_type: 'person' } },
    { id: 'album-1', type: 'album', label: 'Iron Maiden', roles: ['album'], attributes: { year: 1980, band_name: 'Iron Maiden' } },
  ],
  edges: [
    {
      source: 'producer-1',
      target: 'album-1',
      layer: 'producer_album',
      role: 'producer',
      weight: 1,
      support_ratio: 1,
      supporting_recordings: 9,
      album_recordings: 9,
      album_count: null,
      evidence: {},
    },
  ],
  meta: {
    view: 'albums',
    analysis_run_id: 'run-1',
    analysis_version: 'net-test',
    dataset_version: 'mb-test',
    taxonomy_version: '0.2.0',
    graph_version: '0.1.0',
    truncated: false,
    limits: { limit: 20, depth: 1, max_nodes: 500, max_edges: 2000 },
  },
}


const bandsGraph = {
  ...graph,
  nodes: [
    graph.nodes[0],
    { id: 'band-1', type: 'band', label: 'Iron Maiden', roles: ['band'], attributes: { band_type: 'group' } },
  ],
  edges: [
    {
      source: 'producer-1',
      target: 'band-1',
      layer: 'producer_band',
      role: 'mixed',
      weight: 2,
      support_ratio: null,
      supporting_recordings: null,
      album_recordings: null,
      album_count: 2,
      evidence: { role_mix: { producer: 2 } },
    },
  ],
  meta: { ...graph.meta, view: 'bands' },
}

function renderGraph(route = '/producers/producer-1/graph?view=albums') {
  return renderWithProviders(
    <Routes><Route path="/producers/:producerId/graph" element={<ProducerGraphPage />} /></Routes>,
    { route },
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('ProducerGraphPage', () => {
  it('loads a graph and updates view parameters', async () => {
    const fetchMock = mockFetchRoutes({ '/api/v1/producers/producer-1/graph': { body: graph } })
    renderGraph()

    expect(await screen.findByRole('heading', { name: 'Martin Birch' })).toBeInTheDocument()
    expect(screen.getByTestId('producer-graph')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Bands' }))
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/producers/producer-1/graph?view=bands&limit=20&depth=1&max_nodes=500&max_edges=2000&include_evidence=true',
        expect.anything(),
      )
    })
  })


  it('shows truncation and recovers from an invalid view', async () => {
    mockFetchRoutes({
      '/api/v1/producers/producer-1/graph': { body: { ...bandsGraph, meta: { ...bandsGraph.meta, truncated: true } } },
    })
    renderGraph('/producers/producer-1/graph?view=unknown')
    expect(await screen.findByText(/truncated at the server limits/)).toBeInTheDocument()
    expect(screen.getByText(/Unknown graph view/)).toBeInTheDocument()
  })

  it('shows a filtered-empty state and clears filters', async () => {
    mockFetchRoutes({ '/api/v1/producers/producer-1/graph': { body: graph } })
    renderGraph()
    await screen.findByRole('heading', { name: 'Martin Birch' })
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'co-producer' } })
    expect(await screen.findByText('No edges match these filters.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear graph filters' }))
    expect(screen.queryByText('No edges match these filters.')).not.toBeInTheDocument()
  })

  it('shows an empty graph state', async () => {
    mockFetchRoutes({
      '/api/v1/producers/producer-1/graph': { body: { ...graph, nodes: [], edges: [] } },
    })
    renderGraph()
    expect(await screen.findByText('No documented graph nodes for this producer.')).toBeInTheDocument()
  })

  it('shows not-found for an unknown producer', async () => {
    mockFetchRoutes({ '/api/v1/producers/missing/graph': { status: 404, body: {} } })
    renderGraph('/producers/missing/graph?view=bands')
    expect(await screen.findByText('Producer not found.')).toBeInTheDocument()
  })
})
