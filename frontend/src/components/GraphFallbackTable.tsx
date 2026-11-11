import type { GraphTableEdge, GraphTableNode } from '../graph/adapter'

type GraphFallbackTableProps = {
  nodes: GraphTableNode[]
  edges: GraphTableEdge[]
}

export function GraphFallbackTable({ nodes, edges }: GraphFallbackTableProps) {
  return (
    <details className="graph-table-fallback">
      <summary>View the network as tables</summary>

      <div className="table-wrap" tabIndex={0} aria-label="Graph nodes table">
        <table className="data-table">
          <caption className="sr-only">Loaded graph nodes</caption>
          <thead>
            <tr><th scope="col">Node</th><th scope="col">Type</th><th scope="col">Year</th><th scope="col">Detail</th></tr>
          </thead>
          <tbody>
            {nodes.map((node) => (
              <tr key={node.id}>
                <th scope="row">{node.label}</th>
                <td>{node.type}</td>
                <td>{node.year ?? 'Unknown'}</td>
                <td>{node.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-wrap" tabIndex={0} aria-label="Graph edges table">
        <table className="data-table">
          <caption className="sr-only">Loaded graph edges</caption>
          <thead>
            <tr><th scope="col">From</th><th scope="col">To</th><th scope="col">Role</th><th scope="col">Support</th><th scope="col">Albums</th></tr>
          </thead>
          <tbody>
            {edges.map((edge) => (
              <tr key={edge.id}>
                <th scope="row">{edge.sourceLabel}</th>
                <td>{edge.targetLabel}</td>
                <td>{edge.role}</td>
                <td>{edge.support}</td>
                <td>{edge.albumCount ?? 'Single album'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
