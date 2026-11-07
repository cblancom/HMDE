import type { components } from './schema'
import { getJson } from './client'

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
}

export function getBands(filters: BandFilters = {}): Promise<BandListResponse> {
  const params = new URLSearchParams()
  if (filters.q) {
    params.set('q', filters.q)
  }
  if (filters.subgenre) {
    params.set('subgenre', filters.subgenre)
  }
  const query = params.toString()

  return getJson<BandListResponse>(`/api/v1/bands${query ? `?${query}` : ''}`)
}

export function getBand(bandId: string): Promise<BandDetailResponse> {
  return getJson<BandDetailResponse>(`/api/v1/bands/${encodeURIComponent(bandId)}`)
}

export function getBandGraph(bandId: string): Promise<BandGraphResponse> {
  return getJson<BandGraphResponse>(
    `/api/v1/bands/${encodeURIComponent(bandId)}/graph`,
  )
}
