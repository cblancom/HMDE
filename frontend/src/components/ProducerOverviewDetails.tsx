import { Link } from 'react-router'

import type { ProducerGraphEdge, ProducerGraphNode } from '../api/producerGraph'

type ProducerOverviewDetailsProps = {
  node: ProducerGraphNode | null
  edge: ProducerGraphEdge | null
  nodes: ProducerGraphNode[]
  incidentProducers: ProducerGraphNode[]
}

export function ProducerOverviewDetails({
  node,
  edge,
  nodes,
  incidentProducers,
}: ProducerOverviewDetailsProps) {
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
        <p>Select a producer, band, album or edge to inspect its documented evidence.</p>
      </aside>
    )
  }

  if (node.type === 'producer') {
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
        <p className="graph-details__links">
          <Link to={`/producers/${node.id}`}>Open producer details</Link>
          <Link className="button button--secondary" to={`/producers/${node.id}/graph`}>
            Open ego graph
          </Link>
        </p>
      </aside>
    )
  }

  const entityPath = node.type === 'album' ? `/albums/${node.id}` : `/bands/${node.id}`
  return (
    <aside className="graph-details" aria-label="Graph details">
      <h2>{node.label}</h2>
      <dl className="metadata">
        <div><dt>Type</dt><dd>{node.type === 'album' ? 'Album' : 'Band'}</dd></div>
        {typeof node.attributes.year === 'number' ? (
          <div><dt>Year</dt><dd>{node.attributes.year}</dd></div>
        ) : null}
        {typeof node.attributes.band_name === 'string' ? (
          <div><dt>Band</dt><dd>{node.attributes.band_name}</dd></div>
        ) : null}
        <div><dt>Producers</dt><dd>{incidentProducers.length}</dd></div>
        <div><dt>Roles</dt><dd>{node.roles.join(', ')}</dd></div>
      </dl>

      <section aria-labelledby="overview-connected-producers" className="graph-details__producers">
        <h3 id="overview-connected-producers">Connected producers</h3>
        {incidentProducers.length === 0 ? (
          <p>No documented producers are connected to this node.</p>
        ) : (
          <ul>
            {incidentProducers.map((producer) => (
              <li key={producer.id}>
                <Link to={`/graph?selected=${producer.id}`}>{producer.label}</Link>
                <Link to={`/producers/${producer.id}/graph`}>Ego graph</Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="graph-details__links">
        <Link to={entityPath}>Open {node.type} details</Link>
      </p>
    </aside>
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
