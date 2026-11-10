import cytoscape from 'cytoscape'
import { useEffect, useRef } from 'react'

import type { BandGraphResponse } from '../api/bands'

export function BandGraph({ graph }: { graph: BandGraphResponse }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const bandLabel =
    graph.nodes.find((node) => node.type === 'band')?.label ?? 'this band'
  const hasEdges = graph.edges.length > 0

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const elements = [
      ...graph.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          kind: node.type,
        },
      })),
      ...graph.edges.map((edge) => ({
        data: {
          id: `${edge.source}->${edge.target}`,
          source: edge.source,
          target: edge.target,
          label: edge.role,
          albums: edge.albums.join(', '),
        },
      })),
    ]

    let cy: cytoscape.Core
    try {
      cy = cytoscape({
        container,
        elements,
        style: [
          {
            selector: 'node',
            style: {
              label: 'data(label)',
              color: '#14201e',
              'font-size': 10,
              'text-valign': 'bottom',
              'text-margin-y': 4,
              'text-wrap': 'wrap',
              'text-max-width': '120px',
            },
          },
          {
            selector: 'node[kind = "band"]',
            style: {
              shape: 'round-rectangle',
              width: 64,
              height: 30,
              'background-color': '#7a5a20',
            },
          },
          {
            selector: 'node[kind = "producer"]',
            style: {
              shape: 'ellipse',
              width: 28,
              height: 28,
              'background-color': '#8f3b28',
            },
          },
          {
            selector: 'edge',
            style: {
              width: 2,
              'line-color': '#66736d',
              'target-arrow-color': '#66736d',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              label: 'data(label)',
              color: '#14201e',
              'font-size': 9,
              'text-rotation': 'autorotate',
              'text-background-color': '#f4f4ee',
              'text-background-opacity': 0.8,
              'text-background-padding': '2px',
            },
          },
        ],
        layout: {
          name: 'breadthfirst',
          directed: true,
          padding: 24,
          animate: false,
        },
      })
    } catch {
      return
    }

    return () => {
      cy.destroy()
    }
  }, [graph])

  return (
    <section className="graph-section" aria-labelledby="graph-heading">
      <h2 id="graph-heading">Producer graph</h2>
      <p className="graph-meta">Fixture {graph.meta.fixture_version}</p>
      <ul className="graph-legend" aria-label="Graph legend">
        <li>
          <span className="legend-swatch legend-swatch--band" aria-hidden="true" />
          Band
        </li>
        <li>
          <span className="legend-swatch legend-swatch--producer" aria-hidden="true" />
          Producer
        </li>
        <li>
          <span className="legend-swatch legend-swatch--edge" aria-hidden="true" />
          Produced (role on edge)
        </li>
      </ul>

      <div
        ref={containerRef}
        className="graph-canvas"
        data-testid="band-graph"
        role="img"
        aria-label={`Producer graph for ${bandLabel}`}
      />

      {hasEdges ? null : (
        <p className="empty-credits">
          No documented producer credits. Absence is not evidence of non-participation.
        </p>
      )}

      {hasEdges ? (
        <div className="table-wrap">
          <table className="data-table graph-table">
            <caption className="sr-only">Producer graph fallback</caption>
            <thead>
              <tr>
                <th scope="col">Producer</th>
                <th scope="col">Role</th>
                <th scope="col">Albums</th>
              </tr>
            </thead>
            <tbody>
              {graph.edges.map((edge) => {
                const producer = graph.nodes.find((node) => node.id === edge.target)
                return (
                  <tr key={`${edge.source}-${edge.target}`}>
                    <th scope="row">{producer?.label ?? edge.target}</th>
                    <td>{edge.role}</td>
                    <td>{edge.albums.join(', ')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
