import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { getBands } from '../api/bands'
import { ApiError } from '../api/client'
import {
  getProducerOverviewGraph,
  type GraphLayoutMode,
  type ProducerGraphView,
  type ProducerOverviewSort,
} from '../api/producerGraph'
import { queryKeys } from '../api/queryKeys'
import { AsyncState } from '../components/AsyncState'
import { GraphFallbackTable } from '../components/GraphFallbackTable'
import { GraphLegend } from '../components/GraphLegend'
import { OverviewIndex } from '../components/OverviewIndex'
import { ProducerGraph } from '../components/ProducerGraph'
import {
  ProducerOverviewControls,
  type OverviewDisplayOptions,
  type OverviewOptions,
} from '../components/ProducerOverviewControls'
import { ProducerOverviewDetails } from '../components/ProducerOverviewDetails'
import {
  adaptOverviewGraph,
  buildBandIndex,
  buildProducerIndex,
  type GraphRole,
} from '../graph/adapter'

const SORTS: ProducerOverviewSort[] = ['album_count', 'band_count', 'betweenness', 'name']

function parseView(value: string | null): ProducerGraphView {
  return value === 'albums' ? 'albums' : 'bands'
}

function parseProducerLimit(value: string | null): number {
  if (!value || value === 'all') return 0
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0
}

function parseSort(value: string | null): ProducerOverviewSort {
  return value && SORTS.includes(value as ProducerOverviewSort)
    ? (value as ProducerOverviewSort)
    : 'album_count'
}

function parseDecade(value: string | null): string {
  return value && /^\d{4}s$/.test(value) ? value : ''
}

function parseLayout(value: string | null): GraphLayoutMode {
  return value === 'bipartite' || value === 'community' ? value : 'force'
}

function edgeId(edge: { source: string; target: string; role: string }): string {
  return `${edge.source}->${edge.target}:${edge.role}`
}

function adaptResponse(
  response: Parameters<typeof adaptOverviewGraph>[0],
  view: ProducerGraphView,
  role: OverviewDisplayOptions['role'],
  hideIsolated: boolean,
) {
  try {
    return adaptOverviewGraph(response, view, {
      role,
      decade: '',
      subgenre: '',
      hideIsolated,
    })
  } catch {
    return null
  }
}

export function ProducerOverviewPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawView = searchParams.get('view')
  const invalidView = rawView !== null && rawView !== 'albums' && rawView !== 'bands'
  const options: OverviewOptions = {
    view: parseView(rawView),
    producerLimit: parseProducerLimit(searchParams.get('producers')),
    producerSort: parseSort(searchParams.get('sort')),
    order: searchParams.get('order') === 'asc' ? 'asc' : 'desc',
    decade: parseDecade(searchParams.get('decade')),
    subgenre: searchParams.get('subgenre') ?? '',
    layout: parseLayout(searchParams.get('layout')),
  }
  const [displayState, setDisplayState] = useState<{
    role: GraphRole
    producerSearch: string
  }>({ role: 'all', producerSearch: '' })
  const [indexOpen, setIndexOpen] = useState(true)
  const [detailsOpen, setDetailsOpen] = useState(true)
  const display: OverviewDisplayOptions = {
    ...displayState,
    hideIsolated: searchParams.get('isolated') === '0',
  }

  const graphQuery = useQuery({
    queryKey: queryKeys.producerOverviewGraph({
      view: options.view,
      producers: options.producerLimit,
      sort: options.producerSort,
      order: options.order,
      decade: options.decade,
      subgenre: options.subgenre,
      layout: options.layout,
    }),
    queryFn: () =>
      getProducerOverviewGraph({
        view: options.view,
        producerLimit: options.producerLimit,
        producerSort: options.producerSort,
        order: options.order,
        decade: options.decade || undefined,
        subgenre: options.subgenre || undefined,
        includeIsolated: true,
        includeEvidence: options.view === 'bands',
        maxNodes: 1000,
        maxEdges: 2000,
        layout: options.layout === 'force' ? undefined : options.layout,
      }),
  })

  const bandsQuery = useQuery({
    queryKey: queryKeys.bands({
      limit: 200,
      decade: options.decade || undefined,
      subgenre: options.subgenre || undefined,
    }),
    queryFn: () =>
      getBands({
        limit: 200,
        decade: options.decade || undefined,
        subgenre: options.subgenre || undefined,
      }),
  })

  const view = options.view
  const role = displayState.role
  const hideIsolated = searchParams.get('isolated') === '0'
  const adapted = useMemo(
    () => (graphQuery.data ? adaptResponse(graphQuery.data, view, role, hideIsolated) : null),
    [graphQuery.data, view, role, hideIsolated],
  )

  function replaceParams(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(next)) {
      if (value === null || value === '') params.delete(key)
      else params.set(key, value)
    }
    setSearchParams(params)
  }

  function updateOptions(next: OverviewOptions) {
    replaceParams({
      view: next.view === 'bands' ? null : next.view,
      producers: next.producerLimit > 0 ? String(next.producerLimit) : null,
      sort: next.producerSort === 'album_count' ? null : next.producerSort,
      order: next.order === 'desc' ? null : next.order,
      decade: next.decade || null,
      subgenre: next.subgenre || null,
      layout: next.layout === 'force' ? null : next.layout,
      selected: null,
    })
  }

  function updateDisplay(next: OverviewDisplayOptions) {
    setDisplayState({ role: next.role, producerSearch: next.producerSearch })
    replaceParams({
      isolated: next.hideIsolated ? '0' : null,
      selected: null,
    })
  }

  function updateSelected(id: string) {
    if (id) setDetailsOpen(true)
    replaceParams({ selected: id || null })
  }

  function resetFilters() {
    setDisplayState({ role: 'all', producerSearch: '' })
    setSearchParams(new URLSearchParams())
  }

  if (graphQuery.isPending) {
    return <AsyncState status="loading" message="Loading the producer overview…" />
  }

  if (graphQuery.isError) {
    const unavailable = graphQuery.error instanceof ApiError && graphQuery.error.status === 503
    return (
      <section className="page graph-page" aria-labelledby="overview-heading">
        <header className="page-header">
          <h1 id="overview-heading">Producer network</h1>
        </header>
        <AsyncState
          status="error"
          message={
            unavailable
              ? 'No completed analysis run is available for the producer network.'
              : 'Could not load the producer overview.'
          }
          onRetry={() => void graphQuery.refetch()}
        />
      </section>
    )
  }

  const graph = graphQuery.data
  if (graph.nodes.length === 0) {
    return (
      <section className="page graph-page" aria-labelledby="overview-heading">
        <header className="page-header">
          <h1 id="overview-heading">Producer network</h1>
        </header>
        <AsyncState status="empty" message="No producers match these filters." />
      </section>
    )
  }

  const producerIndex = buildProducerIndex(graph.nodes)
  const bandIndex = bandsQuery.data ? buildBandIndex(bandsQuery.data.items) : []
  const adaptationFailed = !adapted
  const selectedId = searchParams.get('selected') ?? ''
  const selectedNode = adapted?.nodes.find((node) => node.id === selectedId) ?? null
  const selectedEdge = adapted?.edges.find((edge) => edgeId(edge) === selectedId) ?? null
  const incidentProducers = selectedNode
    ? (adapted?.allIncidentProducersById[selectedNode.id] ?? [])
    : []
  const search = display.producerSearch.trim().toLocaleLowerCase()
  const searchMatches =
    adapted && search.length > 0
      ? adapted.nodes.filter(
          (node) => node.type === 'producer' && node.label.toLocaleLowerCase().includes(search),
        ).length
      : 0
  const activeServerFilters =
    options.producerLimit > 0 ||
    options.decade !== '' ||
    options.subgenre !== '' ||
    options.view !== 'bands' ||
    options.producerSort !== 'album_count' ||
    options.order !== 'desc'
  const activeDisplayFilters =
    display.role !== 'all' ||
    display.hideIsolated ||
    display.producerSearch.trim() !== ''
  const filteredEmpty =
    Boolean(adapted) &&
    graph.edges.length > 0 &&
    adapted !== null &&
    adapted.counts.edges === 0 &&
    (activeServerFilters || activeDisplayFilters)

  return (
    <section className="page graph-page" aria-labelledby="overview-heading">
      <header className="page-header">
        <p className="eyebrow">Global producer overview</p>
        <h1 id="overview-heading">Producer network</h1>
        <p>
          Explore every documented producer and the bands or albums they shaped. Shared nodes
          connect to each credited producer; no producer–producer edges are implied.
        </p>
      </header>

      <ProducerOverviewControls
        options={options}
        display={display}
        onOptionsChange={updateOptions}
        onDisplayChange={updateDisplay}
        onReset={resetFilters}
      />

      {invalidView ? (
        <p className="async-state" role="status">
          Unknown graph view. Showing bands.
        </p>
      ) : null}
      {graph.meta.truncated ? (
        <p className="async-state" role="status">
          This overview is truncated at the server limits. Filters apply only to the loaded
          network.
        </p>
      ) : null}

      <div className="overview-toolbar">
        <p className="graph-meta" role="status">
          {adapted?.counts.nodes ?? graph.nodes.length} nodes ·{' '}
          {adapted?.counts.edges ?? graph.edges.length} edges ·{' '}
          {adapted?.counts.producers ?? 0} producers · {graph.meta.analysis_version}
          {display.hideIsolated && adapted
            ? ` · ${adapted.counts.hiddenIsolatedProducers} isolated ${
                adapted.counts.hiddenIsolatedProducers === 1 ? 'producer' : 'producers'
              } hidden`
            : ''}
        </p>
        <div className="overview-panel-toggles" role="group" aria-label="Workspace panels">
          <button
            type="button"
            className={indexOpen ? 'button' : 'button button--secondary'}
            aria-pressed={indexOpen}
            onClick={() => setIndexOpen((open) => !open)}
          >
            Index
          </button>
          <button
            type="button"
            className={detailsOpen ? 'button' : 'button button--secondary'}
            aria-pressed={detailsOpen}
            onClick={() => setDetailsOpen((open) => !open)}
          >
            Details
          </button>
        </div>
      </div>
      {search.length > 0 ? (
        <p className="graph-meta" role="status">
          {searchMatches} {searchMatches === 1 ? 'producer matches' : 'producers match'} the
          highlight.
        </p>
      ) : null}

      {adaptationFailed ? (
        <AsyncState
          status="error"
          message="The overview response does not match the selected view."
          onRetry={() => void graphQuery.refetch()}
        />
      ) : null}
      {options.layout !== 'force' && adapted && adapted.layout === null ? (
        <p className="async-state" role="status">
          The requested layout is unavailable. Showing the Force layout.
        </p>
      ) : null}
      {filteredEmpty ? (
        <div className="graph-empty">
          <p>No nodes or edges match these filters.</p>
          <button type="button" className="button button--secondary" onClick={resetFilters}>
            Reset filters
          </button>
        </div>
      ) : null}

      <div
        className={`overview-workspace${
          indexOpen ? '' : ' overview-workspace--index-closed'
        }${detailsOpen ? '' : ' overview-workspace--details-closed'}`}
      >
        {indexOpen ? (
          <OverviewIndex
            producers={producerIndex}
            bands={bandIndex}
            bandsLoading={bandsQuery.isPending}
            bandsError={bandsQuery.isError}
            onRetryBands={() => void bandsQuery.refetch()}
          />
        ) : null}
        <div className="overview-graph-column">
          {adapted ? (
            <ProducerGraph
              graph={adapted}
              variant="overview"
              highlightSearch={display.producerSearch}
              onSelect={(id) => updateSelected(id)}
            />
          ) : null}
        </div>
        {detailsOpen ? (
          <div className="overview-details-column">
            <ProducerOverviewDetails
              node={selectedNode}
              edge={selectedEdge}
              nodes={adapted?.nodes ?? []}
              incidentProducers={incidentProducers}
              selectionMissing={selectedId.length > 0 && !selectedNode && !selectedEdge}
            />
          </div>
        ) : null}
      </div>
      <GraphLegend yearRange={adapted?.yearRange} />
      <GraphFallbackTable nodes={adapted?.tableNodes ?? []} edges={adapted?.tableEdges ?? []} />
      <p>
        <Link to="/producers">← Back to producers</Link>
      </p>
    </section>
  )
}
