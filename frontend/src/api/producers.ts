import type { components } from './schema'
import { buildQuery, getJson } from './client'

type Schemas = components['schemas']

export type ProducerListItem = Schemas['ProducerListItem']
export type ProducerListResponse = Schemas['ProducerListResponse']
export type ProducerDetailResponse = Schemas['ProducerDetailResponse']

export type ProducerSort = 'album_count' | 'band_count' | 'betweenness' | 'name'

export type ProducerFilters = {
  q?: string
  decade?: string
  subgenre?: string
  sort?: ProducerSort
  order?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export function getProducers(filters: ProducerFilters = {}): Promise<ProducerListResponse> {
  return getJson<ProducerListResponse>(
    `/api/v1/producers${buildQuery({
      q: filters.q,
      decade: filters.decade,
      subgenre: filters.subgenre,
      sort: filters.sort,
      order: filters.order,
      limit: filters.limit,
      offset: filters.offset,
    })}`,
  )
}

export function getProducer(producerId: string): Promise<ProducerDetailResponse> {
  return getJson<ProducerDetailResponse>(
    `/api/v1/producers/${encodeURIComponent(producerId)}`,
  )
}
