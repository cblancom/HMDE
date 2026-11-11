import type { components } from './schema'
import { buildQuery, getJson } from './client'

type Schemas = components['schemas']

export type ProducerGraphResponse = Schemas['ProducerGraphResponse']
export type ProducerGraphNode = Schemas['ProducerGraphNode']
export type ProducerGraphEdge = Schemas['ProducerGraphEdge']
export type ProducerGraphView = 'albums' | 'bands'

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
