import type { components } from './schema'
import { getJson } from './client'

type Schemas = components['schemas']

export type TaxonomyResponse = Schemas['TaxonomyResponse']
export type TaxonomyNode = Schemas['TaxonomyNodeResponse']

export function getTaxonomy(): Promise<TaxonomyResponse> {
  return getJson<TaxonomyResponse>('/api/v1/taxonomy')
}
