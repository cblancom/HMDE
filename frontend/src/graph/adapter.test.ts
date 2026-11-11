import { describe, expect, it } from 'vitest'

import type { ProducerGraphResponse } from '../api/producerGraph'
import { adaptGraph, yearColor } from './adapter'

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
