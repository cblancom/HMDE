import { afterEach, describe, expect, it, vi } from 'vitest'

import { getAlbums } from './albums'
import { buildQuery } from './client'
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
