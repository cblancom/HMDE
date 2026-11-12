import type { components } from './schema'
import { buildQuery, getJson } from './client'

type Schemas = components['schemas']

export type ProducerGraphResponse = Schemas['ProducerGraphResponse']
export type ProducerGraphNode = Schemas['ProducerGraphNode']
export type ProducerGraphEdge = Schemas['ProducerGraphEdge']
export type ProducerOverviewGraphResponse = Schemas['ProducerOverviewGraphResponse']
export type ProducerOverviewGraphMeta = Schemas['ProducerOverviewGraphMeta']
export type ProducerOverviewGraphLayout = Schemas['ProducerOverviewGraphLayout']
export type ProducerGraphView = 'albums' | 'bands'
export type ProducerOverviewLayout = 'bipartite' | 'community'
export type GraphLayoutMode = 'force' | ProducerOverviewLayout
export type ProducerOverviewSort = 'album_count' | 'band_count' | 'betweenness' | 'name'

export type ProducerGraphOptions = {
  producerId: string
  view: ProducerGraphView
  limit?: number
  depth?: number
  maxNodes?: number
  maxEdges?: number
  includeEvidence?: boolean
  analysisRun?: string
}

export type ProducerOverviewGraphOptions = {
  view: ProducerGraphView
  producerLimit?: number
  producerSort?: ProducerOverviewSort
  order?: 'asc' | 'desc'
  decade?: string
  subgenre?: string
  includeIsolated?: boolean
  includeEvidence?: boolean
  maxNodes?: number
  maxEdges?: number
  layout?: ProducerOverviewLayout
  analysisRun?: string
}

export function getProducerOverviewGraph({
  view,
  producerLimit = 0,
  producerSort = 'album_count',
  order = 'desc',
  decade,
  subgenre,
  includeIsolated = true,
  includeEvidence = false,
  maxNodes = 1000,
  maxEdges = 2000,
  layout,
  analysisRun,
}: ProducerOverviewGraphOptions): Promise<ProducerOverviewGraphResponse> {
  return getJson<ProducerOverviewGraphResponse>(
    `/api/v1/graph/producers${buildQuery({
      view,
      producer_limit: producerLimit,
      producer_sort: producerSort,
      order,
      decade,
      subgenre,
      include_isolated: includeIsolated,
      include_evidence: includeEvidence,
      max_nodes: maxNodes,
      max_edges: maxEdges,
      layout,
      analysis_run: analysisRun,
    })}`,
  )
}

export function getProducerGraph({
  producerId,
  view,
  limit = 20,
  depth = 1,
  maxNodes = 500,
  maxEdges = 2000,
  includeEvidence = true,
  analysisRun,
}: ProducerGraphOptions): Promise<ProducerGraphResponse> {
  return getJson<ProducerGraphResponse>(
    `/api/v1/producers/${encodeURIComponent(producerId)}/graph${buildQuery({
      view,
      limit,
      depth,
      max_nodes: maxNodes,
      max_edges: maxEdges,
      include_evidence: includeEvidence,
      analysis_run: analysisRun,
    })}`,
  )
}
