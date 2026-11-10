import type { components } from './schema'
import { buildQuery, getJson } from './client'

type Schemas = components['schemas']

export type SearchResponse = Schemas['SearchResponse']

export function searchEntities(q: string, limit = 10): Promise<SearchResponse> {
  return getJson<SearchResponse>(`/api/v1/search${buildQuery({ q, limit })}`)
}
