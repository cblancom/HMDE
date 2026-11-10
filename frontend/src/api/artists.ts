import type { components } from './schema'
import { getJson } from './client'

type Schemas = components['schemas']

export type ArtistDetailResponse = Schemas['ArtistDetailResponse']

export function getArtist(artistId: string): Promise<ArtistDetailResponse> {
  return getJson<ArtistDetailResponse>(`/api/v1/artists/${encodeURIComponent(artistId)}`)
}
