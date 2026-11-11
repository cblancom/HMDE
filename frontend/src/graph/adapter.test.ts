import { describe, expect, it } from 'vitest'

import type { ProducerGraphResponse, ProducerOverviewGraphResponse } from '../api/producerGraph'
import { adaptGraph, adaptOverviewGraph, isIsolatedProducer, yearColor } from './adapter'

const response: ProducerGraphResponse = {
  nodes: [
    {
      id: 'producer-1',
      type: 'producer',
      label: 'Martin Birch',
      roles: ['producer'],
      attributes: { artist_type: 'person' },
    },
    {
      id: 'album-1',
      type: 'album',
      label: 'Iron Maiden',
      roles: ['album'],
      attributes: { band_name: 'Iron Maiden', year: 1980, decade: '1980s', primary_code: 'heavy-metal' },
    },
    {
      id: 'album-2',
      type: 'album',
      label: 'Killers',
      roles: ['album'],
      attributes: { band_name: 'Iron Maiden', year: 1981, decade: '1980s', primary_code: 'heavy-metal' },
    },
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
    {
      source: 'producer-1',
      target: 'album-2',
      layer: 'producer_album',
      role: 'co-producer',
      weight: 1,
      support_ratio: 0.5,
      supporting_recordings: 4,
      album_recordings: 8,
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

const overviewResponse: ProducerOverviewGraphResponse = {
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
  meta: {
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
  },
}

describe('graph adapter', () => {
  it('maps album graphs without band nodes', () => {
    const graph = adaptGraph(response, 'albums', { role: 'all', decade: '', subgenre: '' }, 'producer-1')
    expect(graph.nodes).toHaveLength(3)
    expect(new Set(graph.nodes.map((node) => node.type))).toEqual(new Set(['producer', 'album']))
    expect(graph.elements.filter((element) => element.group === 'edges')).toHaveLength(2)
  })

  it('filters by role, decade and taxonomy', () => {
    const graph = adaptGraph(
      response,
      'albums',
      { role: 'co-producer', decade: '1980s', subgenre: 'heavy-metal' },
      'producer-1',
    )
    expect(graph.edges.map((edge) => edge.target)).toEqual(['album-2'])
    expect(graph.tableEdges).toHaveLength(1)
  })

  it('keeps the seed producer when filters remove all edges', () => {
    const graph = adaptGraph(
      response,
      'albums',
      { role: 'co-producer', decade: '1990s', subgenre: '' },
      'producer-1',
    )
    expect(graph.edges).toHaveLength(0)
    expect(graph.nodes.map((node) => node.id)).toEqual(['producer-1'])
  })

  it('rejects mixed views and produces a year color', () => {
    expect(() => adaptGraph(response, 'bands', { role: 'all', decade: '', subgenre: '' }, 'producer-1')).toThrow(
      'Band graph contains album nodes',
    )
    expect(yearColor(1980)).not.toBe(yearColor(2020))
    expect(yearColor(null)).toBe('#66736d')
  })
})

const albumsOverviewResponse: ProducerOverviewGraphResponse = {
  nodes: [
    {
      id: 'producer-1',
      type: 'producer',
      label: 'Alice Producer',
      roles: ['producer'],
      attributes: { artist_type: 'person', album_count: 2, band_count: 1 },
    },
    {
      id: 'producer-2',
      type: 'producer',
      label: 'Bob Producer',
      roles: ['producer'],
      attributes: { artist_type: 'person', album_count: 1, band_count: 1 },
    },
    {
      id: 'album-1',
      type: 'album',
      label: 'Shared Album',
      roles: ['album'],
      attributes: { band_name: 'Band', year: 1991, decade: '1990s', primary_code: 'heavy-metal' },
    },
    {
      id: 'album-2',
      type: 'album',
      label: 'Old Album',
      roles: ['album'],
      attributes: { band_name: 'Band', year: 1985, decade: '1980s', primary_code: 'thrash-metal' },
    },
  ],
  edges: [
    {
      source: 'producer-1',
      target: 'album-1',
      layer: 'producer_album',
      role: 'producer',
      weight: 1,
      support_ratio: 1,
      supporting_recordings: 8,
      album_recordings: 8,
      album_count: null,
      evidence: {},
    },
    {
      source: 'producer-2',
      target: 'album-1',
      layer: 'producer_album',
      role: 'co-producer',
      weight: 1,
      support_ratio: 0.5,
      supporting_recordings: 4,
      album_recordings: 8,
      album_count: null,
      evidence: {},
    },
    {
      source: 'producer-1',
      target: 'album-2',
      layer: 'producer_album',
      role: 'producer',
      weight: 1,
      support_ratio: 1,
      supporting_recordings: 8,
      album_recordings: 8,
      album_count: null,
      evidence: {},
    },
  ],
  meta: {
    ...overviewResponse.meta,
    view: 'albums',
    limits: { producer_limit: 0, max_nodes: 1000, max_edges: 2000 },
  },
}

describe('overview adapter', () => {
  it('lists every incident producer for a shared node and computes degree counts', () => {
    const graph = adaptOverviewGraph(overviewResponse, 'bands', {
      role: 'all',
      decade: '',
      subgenre: '',
    })
    expect(graph.incidentProducersById['band-1'].map((node) => node.id)).toEqual([
      'producer-1',
      'producer-2',
    ])
    expect(graph.degreeById['band-1']).toBe(2)
    expect(graph.counts.nodes).toBe(5)
    expect(graph.counts.edges).toBe(3)
    expect(graph.counts.producers).toBe(3)
    expect(graph.counts.bands).toBe(2)
    expect(graph.tableNodes.find((node) => node.id === 'band-1')?.detail).toContain(
      'Producers: Alice Producer, Bob Producer',
    )
  })

  it('hides isolated producers and their edges on request', () => {
    const graph = adaptOverviewGraph(overviewResponse, 'bands', {
      role: 'all',
      decade: '',
      subgenre: '',
      hideIsolated: true,
    })
    expect(graph.nodes.map((node) => node.id)).not.toContain('producer-3')
    expect(graph.counts.hiddenIsolatedProducers).toBe(1)
    expect(isIsolatedProducer(overviewResponse.nodes[2])).toBe(true)
    expect(isIsolatedProducer(overviewResponse.nodes[0])).toBe(false)
  })

  it('keeps a shared band with the producer role visible in the bands view', () => {
    const bandProducer = {
      id: 'band-producer',
      type: 'band' as const,
      label: 'Self-produced Band',
      roles: ['band', 'producer'],
      attributes: { band_type: 'group', band_count: 0 },
    }
    const responseWithBandProducer: ProducerOverviewGraphResponse = {
      ...overviewResponse,
      nodes: [...overviewResponse.nodes, bandProducer],
      edges: [
        ...overviewResponse.edges,
        {
          source: 'producer-1',
          target: bandProducer.id,
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
    }
    expect(isIsolatedProducer(bandProducer)).toBe(false)
    const visible = adaptOverviewGraph(responseWithBandProducer, 'bands', {
      role: 'all',
      decade: '',
      subgenre: '',
    })
    expect(visible.nodes.map((node) => node.id)).toContain('band-producer')

    const hidden = adaptOverviewGraph(responseWithBandProducer, 'bands', {
      role: 'all',
      decade: '',
      subgenre: '',
      hideIsolated: true,
    })
    expect(hidden.nodes.map((node) => node.id)).toContain('band-producer')
    expect(hidden.edges.some((edge) => edge.target === 'band-producer')).toBe(true)
  })

  it('filters overview edges by role and rejects a mixed view', () => {
    const graph = adaptOverviewGraph(overviewResponse, 'bands', {
      role: 'co-producer',
      decade: '',
      subgenre: '',
    })
    expect(graph.edges.map((edge) => edge.target)).toEqual(['band-1'])
    expect(graph.nodes.map((node) => node.id)).toEqual(['producer-2', 'producer-3', 'band-1'])

    expect(() =>
      adaptOverviewGraph(
        response as unknown as ProducerOverviewGraphResponse,
        'bands',
        { role: 'all', decade: '', subgenre: '' },
      ),
    ).toThrow('Band graph contains album nodes')
  })

  it('lists incident producers and filters albums by decade and taxonomy', () => {
    const graph = adaptOverviewGraph(albumsOverviewResponse, 'albums', {
      role: 'all',
      decade: '',
      subgenre: '',
    })
    expect(graph.incidentProducersById['album-1'].map((node) => node.id)).toEqual([
      'producer-1',
      'producer-2',
    ])
    expect(graph.supportsDecade).toBe(true)
    expect(graph.availableSubgenres).toEqual(['heavy-metal', 'thrash-metal'])

    const filtered = adaptOverviewGraph(albumsOverviewResponse, 'albums', {
      role: 'all',
      decade: '1990s',
      subgenre: 'heavy-metal',
    })
    expect(filtered.edges.map((edge) => edge.target)).toEqual(['album-1', 'album-1'])
    expect(filtered.nodes.map((node) => node.id)).toEqual([
      'producer-1',
      'producer-2',
      'album-1',
    ])
    expect(filtered.counts.albums).toBe(1)
    expect(filtered.counts.edges).toBe(2)
  })
})
