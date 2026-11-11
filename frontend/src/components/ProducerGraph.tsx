import cytoscape from 'cytoscape'
import d3Force from 'cytoscape-d3-force'
import { useCallback, useEffect, useRef, useState } from 'react'

import type { AdaptedGraph } from '../graph/adapter'
import { graphStyles } from '../graph/styles'

cytoscape.use(d3Force)

type PhysicsState = 'running' | 'frozen'

type ProducerGraphProps = {
  graph: AdaptedGraph
  onSelect?: (id: string, kind: 'node' | 'edge') => void
}

function collideRadiusFor(node: { type?: string }): number {
  if (node.type === 'band') return 34
  if (node.type === 'album') return 28
  return 22
}

function linkDistanceFor(nodeCount: number, canvasHeight: number): number {
  const desired = Math.max(180, Math.min(300, 70 + nodeCount * 11))
  return Math.max(120, Math.min(desired, canvasHeight / 2 - 60))
}

const FORCE_OPTIONS = {
  name: 'd3-force',
  infinite: true,
  fixedAfterDragging: false,
  ungrabifyWhileSimulating: false,
  animate: true,
  fit: false,
  padding: 40,
  randomize: false,
  alpha: 1,
  alphaMin: 0.001,
  alphaDecay: 0.0228,
  velocityDecay: 0.4,
  collideRadius: collideRadiusFor,
  collideStrength: 0.9,
  collideIterations: 2,
  manyBodyStrength: -320,
  linkId: (node: { id: string }) => node.id,
}

export function ProducerGraph({ graph, onSelect }: ProducerGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const layoutRef = useRef<cytoscape.Layouts | null>(null)
  const physicsRef = useRef<PhysicsState>('running')
  const onSelectRef = useRef(onSelect)
  const [physics, setPhysics] = useState<PhysicsState>('running')
  const nodeCount = graph.nodes.length
  const reducedMotion = useRef(
    typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  useEffect(() => {
    onSelectRef.current = onSelect
  }, [onSelect])

  const setPhysicsState = useCallback((next: PhysicsState) => {
    physicsRef.current = next
    setPhysics(next)
  }, [])

  const runForce = useCallback(
    (reheat = false) => {
      const cy = cyRef.current
      if (!cy) return
      layoutRef.current?.stop()
      try {
        const layout = cy.layout({
          ...FORCE_OPTIONS,
          linkDistance: linkDistanceFor(nodeCount, cy.height()),
          randomize: reheat,
        } as unknown as cytoscape.LayoutOptions)
        layout.run()
        layoutRef.current = layout
        setPhysicsState('running')
      } catch {
        layoutRef.current = null
        try {
          cy.layout({ name: 'breadthfirst', directed: false, padding: 40, animate: false }).run()
        } catch {
          // Keep the loaded graph and its fallback table visible.
        }
        setPhysicsState('frozen')
      }
    },
    [nodeCount, setPhysicsState],
  )

  const freeze = useCallback(() => {
    layoutRef.current?.stop()
    setPhysicsState('frozen')
  }, [setPhysicsState])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let cy: cytoscape.Core
    try {
      cy = cytoscape({
        container,
        elements: graph.elements,
        style: graphStyles,
        layout: { name: 'preset', fit: false },
      })
    } catch {
      return
    }
    cyRef.current = cy

    const onSelectEvent = (event: cytoscape.EventObject) => {
      onSelectRef.current?.(event.target.id(), event.target.isNode() ? 'node' : 'edge')
    }
    const onUnselectEvent = () => onSelectRef.current?.('', 'node')
    cy.on('select', 'node, edge', onSelectEvent)
    cy.on('unselect', 'node, edge', onUnselectEvent)

    if (reducedMotion.current) {
      cy.layout({ name: 'breadthfirst', directed: false, padding: 40, animate: false }).run()
      setPhysicsState('frozen')
    } else {
      runForce()
    }

    let wasRunning = !reducedMotion.current
    const onVisibility = () => {
      if (document.hidden) {
        wasRunning = physicsRef.current === 'running'
        freeze()
      } else if (wasRunning && !reducedMotion.current) {
        runForce()
        wasRunning = false
      }
    }
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      cy.removeListener('select', 'node, edge', onSelectEvent)
      cy.removeListener('unselect', 'node, edge', onUnselectEvent)
      layoutRef.current?.stop()
      cy.destroy()
      cyRef.current = null
      layoutRef.current = null
    }
  }, [graph, freeze, runForce, setPhysicsState])

  return (
    <section className="producer-graph" data-testid="producer-graph" aria-labelledby="producer-graph-heading">
      <div className="graph-toolbar">
        <h2 id="producer-graph-heading">Network</h2>
        <div className="graph-actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={freeze}
            disabled={physics === 'frozen'}
          >
            Freeze layout
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => runForce(false)}
            disabled={physics === 'running'}
          >
            Resume physics
          </button>
          <button type="button" className="button button--secondary" onClick={() => runForce(true)}>
            Reheat
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        className="graph-canvas producer-graph-canvas"
        role="img"
        aria-label="Producer network graph"
        data-testid="producer-graph-canvas"
      />
      <p className="graph-meta" role="status">
        {physics === 'running' ? 'Physics running' : 'Layout frozen'}. Drag a node to move the
        network.
      </p>
    </section>
  )
}
