import type { components } from './schema'
import { buildQuery, getJson } from './client'

type Schemas = components['schemas']

export type BandListItem = Schemas['BandListItem']
export type BandListResponse = Schemas['BandListResponse']
export type BandDetailResponse = Schemas['BandDetailResponse']
export type BandGraphResponse = Schemas['BandGraphResponse']
export type CreditResponse = Schemas['CreditResponse']
export type AlbumResponse = Schemas['AlbumResponse']

export type BandFilters = {
  q?: string
  subgenre?: string
  decade?: string
  yearFrom?: number
  yearTo?: number
  limit?: number
  offset?: number
}

export function getBands(filters: BandFilters = {}): Promise<BandListResponse> {
  return getJson<BandListResponse>(
    `/api/v1/bands${buildQuery({
      q: filters.q,
      subgenre: filters.subgenre,
      decade: filters.decade,
      year_from: filters.yearFrom,
      year_to: filters.yearTo,
      limit: filters.limit,
      offset: filters.offset,
    })}`,
  )
}

const BAND_INDEX_PAGE_SIZE = 200

export async function getAllBands(filters: BandFilters = {}): Promise<BandListItem[]> {
  const first = await getBands({
    ...filters,
    limit: BAND_INDEX_PAGE_SIZE,
    offset: 0,
  })
  const items = [...first.items]
  while (items.length < first.total) {
    const page = await getBands({
      ...filters,
      limit: BAND_INDEX_PAGE_SIZE,
      offset: items.length,
    })
    if (page.items.length === 0) break
    items.push(...page.items)
  }
  return items
}

export function getBand(bandId: string): Promise<BandDetailResponse> {
  return getJson<BandDetailResponse>(`/api/v1/bands/${encodeURIComponent(bandId)}`)
}

export type BandGraphOptions = {
  producerLimit?: number
  maxNodes?: number
}

export function getBandGraph(
  bandId: string,
  { producerLimit = 0, maxNodes = 2000 }: BandGraphOptions = {},
): Promise<BandGraphResponse> {
  return getJson<BandGraphResponse>(
    `/api/v1/bands/${encodeURIComponent(bandId)}/graph${buildQuery({
      producer_limit: producerLimit,
      max_nodes: maxNodes,
    })}`,
  )
}
