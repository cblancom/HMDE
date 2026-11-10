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

export function getBand(bandId: string): Promise<BandDetailResponse> {
  return getJson<BandDetailResponse>(`/api/v1/bands/${encodeURIComponent(bandId)}`)
}

export function getBandGraph(bandId: string): Promise<BandGraphResponse> {
  return getJson<BandGraphResponse>(
    `/api/v1/bands/${encodeURIComponent(bandId)}/graph`,
  )
}
