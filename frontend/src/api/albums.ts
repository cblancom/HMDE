import type { components } from './schema'
import { buildQuery, getJson } from './client'

type Schemas = components['schemas']

export type AlbumListItem = Schemas['AlbumListItem']
export type AlbumListResponse = Schemas['AlbumListResponse']
export type AlbumDetailResponse = Schemas['AlbumDetailResponse']
export type AlbumCreditResponse = Schemas['AlbumCreditResponse']

export type AlbumFilters = {
  q?: string
  bandId?: string
  producerId?: string
  decade?: string
  yearFrom?: number
  yearTo?: number
  subgenre?: string
  includeUnclassified?: boolean
  limit?: number
  offset?: number
}

export function getAlbums(filters: AlbumFilters = {}): Promise<AlbumListResponse> {
  return getJson<AlbumListResponse>(
    `/api/v1/albums${buildQuery({
      q: filters.q,
      band_id: filters.bandId,
      producer_id: filters.producerId,
      decade: filters.decade,
      year_from: filters.yearFrom,
      year_to: filters.yearTo,
      subgenre: filters.subgenre,
      include_unclassified: filters.includeUnclassified,
      limit: filters.limit,
      offset: filters.offset,
    })}`,
  )
}

export function getAlbum(albumId: string): Promise<AlbumDetailResponse> {
  return getJson<AlbumDetailResponse>(`/api/v1/albums/${encodeURIComponent(albumId)}`)
}
