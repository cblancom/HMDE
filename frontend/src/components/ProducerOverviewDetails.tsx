import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { getBand } from '../api/bands'
import {
  getProducerGraph,
  type ProducerGraphEdge,
  type ProducerGraphNode,
} from '../api/producerGraph'
import { queryKeys } from '../api/queryKeys'

type ProducerOverviewDetailsProps = {
  node: ProducerGraphNode | null
  edge: ProducerGraphEdge | null
  nodes: ProducerGraphNode[]
  incidentProducers: ProducerGraphNode[]
  selectionMissing?: boolean
}

type ProducerNeighbors = {
  bands: ProducerGraphNode[]
  albums: ProducerGraphNode[]
  truncated: boolean
}

type BandProducer = {
  id: string
  name: string
}

export function ProducerOverviewDetails({
  node,
  edge,
  nodes,
  incidentProducers,
  selectionMissing = false,
}: ProducerOverviewDetailsProps) {
  const producerId = node?.type === 'producer' ? node.id : ''
  const producerNeighborsQuery = useQuery({
    queryKey: queryKeys.producerNeighbors(producerId),
    queryFn: () => loadProducerNeighbors(producerId),
    enabled: producerId.length > 0,
  })

  const bandId = node?.type === 'band' ? node.id : ''
  const bandQuery = useQuery({
    queryKey: queryKeys.band(bandId),
    queryFn: () => getBand(bandId),
    enabled: bandId.length > 0,
  })

  if (edge) {
    const source = nodes.find((item) => item.id === edge.source)
    const target = nodes.find((item) => item.id === edge.target)
    return (
      <aside className="graph-details" aria-label="Graph details">
        <h2>Selected edge</h2>
        <dl className="metadata">
          <div><dt>From</dt><dd>{source?.label ?? edge.source}</dd></div>
          <div><dt>To</dt><dd>{target?.label ?? edge.target}</dd></div>
          <div><dt>Role</dt><dd>{edge.role}</dd></div>
          <div><dt>Support</dt><dd>{formatSupport(edge.support_ratio)}</dd></div>
          <div><dt>Albums</dt><dd>{edge.album_count ?? 'Single album'}</dd></div>
        </dl>
      </aside>
    )
  }

  if (!node) {
    return (
      <aside className="graph-details" aria-label="Graph details">
        <h2>Details</h2>
        <p>
          {selectionMissing
            ? 'The selected entity is not in the current view. Clear filters or select another node.'
            : 'Select a producer, band, album or edge to inspect its documented evidence.'}
        </p>
      </aside>
    )
  }

  if (node.type === 'producer') {
    const neighbors = producerNeighborsQuery.data
    return (
      <aside className="graph-details" aria-label="Graph details">
        <h2>{node.label}</h2>
        <dl className="metadata">
          <div><dt>Type</dt><dd>Producer</dd></div>
          <div><dt>Albums</dt><dd>{numberAttribute(node, 'album_count') ?? 0}</dd></div>
          <div><dt>Bands</dt><dd>{numberAttribute(node, 'band_count') ?? 0}</dd></div>
          <div><dt>Betweenness</dt><dd>{formatBetweenness(node)}</dd></div>
          <div><dt>Community</dt><dd>{stringAttribute(node, 'community_key') || 'Unassigned'}</dd></div>
          <div><dt>Roles</dt><dd>{node.roles.join(', ')}</dd></div>
        </dl>
        <RelatedState
          isPending={producerNeighborsQuery.isPending}
          isError={producerNeighborsQuery.isError}
          onRetry={() => void producerNeighborsQuery.refetch()}
        />
        {neighbors ? (
          <>
            {neighbors.truncated ? (
              <p className="graph-details__notice">
                One of the ego graphs is truncated at its server limit.
              </p>
            ) : null}
            <RelatedList
              heading="Bands"
              id="producer-bands-heading"
              empty="No documented bands."
              items={neighbors.bands.map((band) => ({
                id: band.id,
                label: band.label,
                to: `/bands/${band.id}`,
              }))}
            />
            <RelatedList
              heading="Albums"
              id="producer-albums-heading"
              empty="No documented albums."
              items={neighbors.albums.map((album) => ({
                id: album.id,
                label: `${album.label}${typeof album.attributes.year === 'number' ? ` (${album.attributes.year})` : ''}`,
                to: `/albums/${album.id}`,
              }))}
            />
          </>
        ) : null}
        <p className="graph-details__links">
          <Link to={`/producers/${node.id}`}>Open producer details</Link>
          <Link className="button button--secondary" to={`/producers/${node.id}/graph`}>
            Open ego graph
          </Link>
        </p>
      </aside>
    )
  }

  if (node.type === 'band') {
    const albumItems = (bandQuery.data?.albums ?? [])
      .map((album) => ({
        id: album.id,
        label: `${album.title}${album.year ? ` (${album.year})` : ''}`,
        to: `/albums/${album.id}`,
      }))
      .sort((left, right) => left.label.localeCompare(right.label))
    const producers = bandProducers(bandQuery.data)
    return (
      <aside className="graph-details" aria-label="Graph details">
        <h2>{node.label}</h2>
        <dl className="metadata">
          <div><dt>Type</dt><dd>Band</dd></div>
          <div><dt>Albums</dt><dd>{bandQuery.data?.albums.length ?? numberAttribute(node, 'album_count') ?? 0}</dd></div>
          <div><dt>Producers</dt><dd>{producers.length}</dd></div>
          <div><dt>Roles</dt><dd>{node.roles.join(', ')}</dd></div>
        </dl>
        <RelatedState
          isPending={bandQuery.isPending}
          isError={bandQuery.isError}
          onRetry={() => void bandQuery.refetch()}
        />
        {bandQuery.data ? (
          <>
            <RelatedList
              heading="Albums"
              id="band-albums-heading"
              empty="No documented albums."
              items={albumItems}
            />
            <RelatedList
              heading="Producers"
              id="band-producers-heading"
              empty="No documented producers."
              items={producers.map((producer) => ({
                id: producer.id,
                label: producer.name,
                to: `/graph?selected=${producer.id}`,
              }))}
            />
          </>
        ) : null}
        <p className="graph-details__links">
          <Link to={`/bands/${node.id}`}>Open band details</Link>
        </p>
      </aside>
    )
  }

  return (
    <aside className="graph-details" aria-label="Graph details">
      <h2>{node.label}</h2>
      <dl className="metadata">
        <div><dt>Type</dt><dd>Album</dd></div>
        {typeof node.attributes.year === 'number' ? (
          <div><dt>Year</dt><dd>{node.attributes.year}</dd></div>
        ) : (
          <div><dt>Year</dt><dd>Year unknown</dd></div>
        )}
        {typeof node.attributes.band_name === 'string' ? (
          <div><dt>Band</dt><dd>{node.attributes.band_name}</dd></div>
        ) : null}
        <div><dt>Producers</dt><dd>{incidentProducers.length}</dd></div>
        <div><dt>Roles</dt><dd>{node.roles.join(', ')}</dd></div>
      </dl>
      <RelatedList
        heading="Producers"
        id="album-producers-heading"
        empty="No documented producers."
        items={incidentProducers.map((producer) => ({
          id: producer.id,
          label: producer.label,
          to: `/graph?selected=${producer.id}`,
        }))}
      />
      <p className="graph-details__links">
        <Link to={`/albums/${node.id}`}>Open album details</Link>
        {typeof node.attributes.band_id === 'string' ? (
          <Link to={`/bands/${node.attributes.band_id}`}>Open band details</Link>
        ) : null}
      </p>
    </aside>
  )
}

async function loadProducerNeighbors(producerId: string): Promise<ProducerNeighbors> {
  const [bands, albums] = await Promise.all([
    getProducerGraph({
      producerId,
      view: 'bands',
      limit: 100,
      depth: 1,
      maxNodes: 500,
      maxEdges: 2000,
      includeEvidence: false,
    }),
    getProducerGraph({
      producerId,
      view: 'albums',
      limit: 100,
      depth: 1,
      maxNodes: 500,
      maxEdges: 2000,
      includeEvidence: false,
    }),
  ])
  return {
    bands: bands.nodes
      .filter((item) => item.id !== producerId)
      .sort((left, right) => left.label.localeCompare(right.label)),
    albums: albums.nodes
      .filter((item) => item.id !== producerId && item.type === 'album')
      .sort(
        (left, right) =>
          yearOf(left) - yearOf(right) ||
          left.label.localeCompare(right.label),
      ),
    truncated: bands.meta.truncated || albums.meta.truncated,
  }
}

function bandProducers(data: Awaited<ReturnType<typeof getBand>> | undefined): BandProducer[] {
  if (!data) return []
  const producers = new Map<string, string>()
  for (const album of data.albums) {
    for (const credit of album.credits) {
      if (credit.role === 'producer' || credit.role === 'co-producer') {
        producers.set(credit.artist_id, credit.artist_name)
      }
    }
  }
  return [...producers.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((left, right) => left.name.localeCompare(right.name))
}

function yearOf(node: ProducerGraphNode): number {
  return typeof node.attributes.year === 'number' ? node.attributes.year : Number.MAX_SAFE_INTEGER
}

function RelatedState({
  isPending,
  isError,
  onRetry,
}: {
  isPending: boolean
  isError: boolean
  onRetry: () => void
}) {
  if (isPending) return <p className="graph-details__notice">Loading related relationships…</p>
  if (!isError) return null
  return (
    <div className="graph-details__notice">
      <p>Related relationships are unavailable.</p>
      <button type="button" className="button button--secondary" onClick={onRetry}>
        Retry
      </button>
    </div>
  )
}

function RelatedList({
  heading,
  id,
  empty,
  items,
}: {
  heading: string
  id: string
  empty: string
  items: Array<{ id: string; label: string; to: string }>
}) {
  return (
    <section aria-labelledby={id} className="graph-details__related">
      <h3 id={id}>{heading}</h3>
      {items.length === 0 ? (
        <p>{empty}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <Link to={item.to}>{item.label}</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function formatSupport(value: number | null): string {
  return value === null ? 'Unknown' : `${Math.round(value * 100)}%`
}

function formatBetweenness(node: ProducerGraphNode): string {
  const value = numberAttribute(node, 'betweenness')
  return value === null ? 'Not available' : value.toFixed(3)
}

function numberAttribute(node: ProducerGraphNode, key: string): number | null {
  const value = node.attributes[key]
  return typeof value === 'number' ? value : null
}

function stringAttribute(node: ProducerGraphNode, key: string): string {
  const value = node.attributes[key]
  return typeof value === 'string' ? value : ''
}
