import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'

import { ApiError } from '../api/client'
import { getProducerGraph, type ProducerGraphView } from '../api/producerGraph'
import { queryKeys } from '../api/queryKeys'
import { AsyncState } from '../components/AsyncState'
import { GraphControls } from '../components/GraphControls'
import { GraphDetails } from '../components/GraphDetails'
import { GraphFallbackTable } from '../components/GraphFallbackTable'
import { GraphFilters } from '../components/GraphFilters'
import { GraphLegend } from '../components/GraphLegend'
import { ProducerGraph } from '../components/ProducerGraph'
import { adaptGraph, type GraphFilters as GraphFilterState } from '../graph/adapter'

function parseView(value: string | null): ProducerGraphView {
  return value === 'albums' ? 'albums' : 'bands'
}

export function ProducerGraphPage() {
  const { producerId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const id = producerId ?? ''
  const rawView = searchParams.get('view')
  const view = parseView(rawView)
  const invalidView = rawView !== null && rawView !== 'albums' && rawView !== 'bands'
  const limit = Number(searchParams.get('limit') ?? 20)
  const depth = Number(searchParams.get('depth') ?? 1)
  const [filters, setFilters] = useState<GraphFilterState>({ role: 'all', decade: '', subgenre: '' })
  const [selection, setSelection] = useState<{ id: string; kind: 'node' | 'edge' } | null>(null)

  const graphQuery = useQuery({
    queryKey: queryKeys.producerGraph(id, { view, limit, depth }),
    queryFn: () => getProducerGraph({ producerId: id, view, limit, depth, includeEvidence: true }),
    enabled: id.length > 0,
  })
  const adapted = useMemo(() => {
    if (!graphQuery.data) return null
    try {
      return adaptGraph(graphQuery.data, view, filters, id)
    } catch {
      return null
    }
  }, [graphQuery.data, view, filters, id])
  const adaptationFailed = Boolean(graphQuery.data && !adapted)

  function updateParams(next: { view?: ProducerGraphView; limit?: number; depth?: number }) {
    const params = new URLSearchParams(searchParams)
    params.set('view', next.view ?? view)
    params.set('limit', String(next.limit ?? limit))
    params.set('depth', String(next.depth ?? depth))
    setSearchParams(params)
  }

  if (!id) return <AsyncState status="not-found" message="Producer not found." />
  if (graphQuery.isPending) return <AsyncState status="loading" message="Loading producer graph…" />

  if (graphQuery.isError) {
    const notFound = graphQuery.error instanceof ApiError && graphQuery.error.status === 404
    return notFound ? (
      <AsyncState status="not-found" message="Producer not found." />
    ) : (
      <AsyncState
        status="error"
        message="Could not load this producer graph."
        onRetry={() => void graphQuery.refetch()}
      />
    )
  }

  const graph = graphQuery.data
  if (adaptationFailed) {
    return (
      <section className="page graph-page" aria-labelledby="graph-page-heading">
        <p><Link to={`/producers/${id}`}>← Back to producer</Link></p>
        <header className="page-header"><h1 id="graph-page-heading">Producer graph</h1></header>
        <AsyncState status="error" message="The graph response does not match the selected view." />
      </section>
    )
  }
  if (graph.nodes.length === 0) {
    return (
      <section className="page graph-page" aria-labelledby="graph-page-heading">
        <p><Link to={`/producers/${id}`}>← Back to producer</Link></p>
        <header className="page-header"><h1 id="graph-page-heading">Producer graph</h1></header>
        <AsyncState status="empty" message="No documented graph nodes for this producer." />
      </section>
    )
  }
  const seed = graph.nodes.find((node) => node.id === id)
  const selectedNode = selection?.kind === 'node' ? adapted?.nodes.find((node) => node.id === selection.id) ?? null : null
  const selectedEdge = selection?.kind === 'edge' ? adapted?.edges.find((edge) => `${edge.source}->${edge.target}:${edge.role}` === selection.id) ?? null : null
  const activeFilters = filters.role !== 'all' || filters.decade !== '' || filters.subgenre !== ''
  const filteredEmpty = Boolean(adapted && graph.edges.length > 0 && adapted.edges.length === 0 && activeFilters)
  const title = seed?.label ?? 'Producer graph'

  return (
    <section className="page graph-page" aria-labelledby="graph-page-heading">
      <p><Link to={`/producers/${id}`}>← Back to producer</Link></p>
      <header className="page-header">
        <p className="eyebrow">{view === 'albums' ? 'Producer albums' : 'Producer bands'}</p>
        <h1 id="graph-page-heading">{title}</h1>
        <p>Move a node to see its documented network respond. Freeze the layout when you want to read it.</p>
      </header>

      <GraphControls
        view={view}
        limit={limit}
        depth={depth}
        onViewChange={(next) => {
          setSelection(null)
          setFilters({ role: 'all', decade: '', subgenre: '' })
          updateParams({ view: next })
        }}
        onLimitChange={(next) => updateParams({ limit: next })}
        onDepthChange={(next) => updateParams({ depth: next })}
      />
      <GraphFilters
        filters={filters}
        decades={adapted?.availableDecades ?? []}
        subgenres={adapted?.availableSubgenres ?? []}
        supportsDecade={adapted?.supportsDecade ?? false}
        supportsSubgenre={adapted?.supportsSubgenre ?? false}
        onChange={(next) => {
          setSelection(null)
          setFilters(next)
        }}
      />

      <p className="graph-meta">
        {graph.nodes.length} nodes · {graph.edges.length} edges · {graph.meta.analysis_version}
      </p>

      {graph.meta.truncated ? (
        <p className="async-state" role="status">
          This graph is truncated at the server limits. Filters apply only to the loaded network.
        </p>
      ) : null}

      {invalidView ? (
        <p className="async-state" role="status">
          Unknown graph view. Showing bands.
        </p>
      ) : null}
      {filteredEmpty ? (
        <div className="graph-empty">
          <p>No edges match these filters.</p>
          <button type="button" className="button button--secondary" onClick={() => setFilters({ role: 'all', decade: '', subgenre: '' })}>
            Clear graph filters
          </button>
        </div>
      ) : null}
      <GraphLegend />
      {adapted ? (
        <ProducerGraph
          graph={adapted}
          onSelect={(id, kind) => setSelection(id ? { id, kind } : null)}
        />
      ) : null}
      <GraphFallbackTable nodes={adapted?.tableNodes ?? []} edges={adapted?.tableEdges ?? []} />
      <GraphDetails node={selectedNode} edge={selectedEdge} nodes={adapted?.nodes ?? []} />
    </section>
  )
}
