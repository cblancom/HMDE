import { Link } from 'react-router'

import type { ProducerGraphEdge, ProducerGraphNode } from '../api/producerGraph'

type GraphDetailsProps = {
  node: ProducerGraphNode | null
  edge: ProducerGraphEdge | null
  nodes: ProducerGraphNode[]
}

export function GraphDetails({ node, edge, nodes }: GraphDetailsProps) {
  if (!node && !edge) {
    return (
      <aside className="graph-details" aria-label="Graph details">
        <h2>Details</h2>
        <p>Select a node or edge to inspect its documented evidence.</p>
      </aside>
    )
  }

  if (edge) {
    const source = nodes.find((item) => item.id === edge.source)
    const target = nodes.find((item) => item.id === edge.target)
    return (
      <aside className="graph-details" aria-label="Graph details">
        <h2>Edge</h2>
        <dl className="metadata">
          <div><dt>From</dt><dd>{source?.label ?? edge.source}</dd></div>
          <div><dt>To</dt><dd>{target?.label ?? edge.target}</dd></div>
          <div><dt>Role</dt><dd>{edge.role}</dd></div>
          <div><dt>Support</dt><dd>{edge.support_ratio === null ? 'Unknown' : `${Math.round(edge.support_ratio * 100)}%`}</dd></div>
          <div><dt>Albums</dt><dd>{edge.album_count ?? 'Single album'}</dd></div>
        </dl>
      </aside>
    )
  }

  if (!node) return null
  const year = node.attributes.year
  return (
    <aside className="graph-details" aria-label="Graph details">
      <h2>{node.label}</h2>
      <dl className="metadata">
        <div><dt>Type</dt><dd>{node.type}</dd></div>
        {typeof year === 'number' ? <div><dt>Year</dt><dd>{year}</dd></div> : null}
        {node.type === 'album' && typeof node.attributes.band_name === 'string' ? (
          <div><dt>Band</dt><dd>{node.attributes.band_name}</dd></div>
        ) : null}
        <div><dt>Roles</dt><dd>{node.roles.join(', ')}</dd></div>
      </dl>
      <p>
        <Link to={nodePath(node)}>Open {node.type} details</Link>
      </p>
    </aside>
  )
}

function nodePath(node: ProducerGraphNode): string {
  if (node.type === 'album') return `/albums/${node.id}`
  if (node.type === 'band') return `/bands/${node.id}`
  return `/producers/${node.id}`
}
