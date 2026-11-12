import { afterEach, describe, expect, it, vi } from 'vitest'

import { getAlbums } from './albums'
import { buildQuery } from './client'
import { getProducerOverviewGraph } from './producerGraph'
import { getProducers } from './producers'
import { searchEntities } from './search'
import { mockFetchRoutes } from '../test/fetch'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API query builders', () => {
  it('omits empty values and encodes query parameters', () => {
    expect(buildQuery({ q: 'iron maiden', offset: 0, limit: undefined })).toBe(
      '?q=iron+maiden&offset=0',
    )
  })

  it('maps camelCase filters to API names', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/albums': { body: { items: [], total: 0, limit: 20, offset: 0 } },
    })
    await getAlbums({ bandId: 'band-1', yearFrom: 1980, includeUnclassified: false })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/albums?band_id=band-1&year_from=1980&include_unclassified=false',
      expect.anything(),
    )
  })

  it('requests the global producer overview with bounded parameters', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/graph/producers': {
        body: {
          nodes: [],
          edges: [],
          meta: {
            scope: 'overview',
            view: 'bands',
            analysis_run_id: 'run-1',
            analysis_version: 'net-test',
            dataset_version: 'mb-test',
            taxonomy_version: '0.2.0',
            graph_version: '0.1.0',
            truncated: false,
            matched_producers: 0,
            selected_producers: 0,
            include_isolated: true,
            limits: { producer_limit: 0, max_nodes: 1000, max_edges: 2000 },
          },
        },
      },
    })
    await getProducerOverviewGraph({
      view: 'bands',
      producerLimit: 5,
      decade: '1990s',
      includeIsolated: false,
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/graph/producers?view=bands&producer_limit=5&producer_sort=album_count&order=desc&decade=1990s&include_isolated=false&include_evidence=false&max_nodes=1000&max_edges=2000',
      expect.anything(),
    )
    await getProducerOverviewGraph({ view: 'bands', layout: 'community' })
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('layout=community'),
      expect.anything(),
    )
  })

  it('requests producer rankings and grouped search', async () => {
    const fetchMock = mockFetchRoutes({
      '/api/v1/producers': { body: { items: [], total: 0, limit: 20, offset: 0 } },
      '/api/v1/search': {
        body: { query: 'iron', bands: [], albums: [], producers: [] },
      },
    })
    await getProducers({ sort: 'band_count', order: 'desc' })
    await searchEntities('iron')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/producers?sort=band_count&order=desc',
      expect.anything(),
    )
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/search?q=iron&limit=10', expect.anything())
  })
})
