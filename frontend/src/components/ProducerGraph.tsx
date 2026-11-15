import cytoscape from 'cytoscape'
import d3Force from 'cytoscape-d3-force'
import fcose from 'cytoscape-fcose'
import { useCallback, useEffect, useRef, useState } from 'react'

import type { AdaptedGraph } from '../graph/adapter'
import {
  DEFAULT_FORCE_ENGINE,
  d3ForceOptions,
  forceEngineOptions,
  isFiniteForceEngine,
  type ForceEngine,
  type GraphVariant,
} from '../graph/forceLayouts'
import { graphStyles } from '../graph/styles'

cytoscape.use(d3Force)
let fcoseAvailable = false
try {
  cytoscape.use(fcose)
  fcoseAvailable = true
} catch {
  fcoseAvailable = false
}

type PhysicsState = 'running' | 'complete' | 'frozen'
export type { GraphVariant }

type ProducerGraphProps = {
  graph: AdaptedGraph
  variant?: GraphVariant
  engine?: ForceEngine
  highlightSearch?: string
  onSelect?: (id: string, kind: 'node' | 'edge') => void
}

function engineLabel(engine: ForceEngine): string {
  if (engine === 'cose') return 'CoSE'
  if (engine === 'fcose') return 'fCoSE'
  return 'd3-force'
}

export function ProducerGraph({
  graph,
  variant = 'ego',
  engine = DEFAULT_FORCE_ENGINE,
  highlightSearch = '',
  onSelect,
}: ProducerGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const layoutRef = useRef<cytoscape.Layouts | null>(null)
  const fitTimerRef = useRef<number | null>(null)
  const runTokenRef = useRef(0)
  const staticLayout = Boolean(graph.layout)
  const reducedMotion =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const finiteEngine = isFiniteForceEngine(engine)
  const frozenStart = staticLayout || (reducedMotion && !finiteEngine)
  const physicsRef = useRef<PhysicsState>(frozenStart ? 'frozen' : 'running')
  const onSelectRef = useRef(onSelect)
  const [physics, setPhysics] = useState<PhysicsState>(frozenStart ? 'frozen' : 'running')
  const [activeEngine, setActiveEngine] = useState<ForceEngine>(engine)
  const [engineNotice, setEngineNotice] = useState<string | null>(null)
  const nodeCount = graph.nodes.length
  const activeFinite = isFiniteForceEngine(activeEngine)
  const displayPhysics = staticLayout || (reducedMotion && !activeFinite) ? 'frozen' : physics

  useEffect(() => {
    onSelectRef.current = onSelect
  }, [onSelect])

  const setPhysicsState = useCallback((next: PhysicsState) => {
    physicsRef.current = next
    setPhysics(next)
  }, [])

  const fitOverview = useCallback(() => {
    const cy = cyRef.current
    if (!cy || typeof cy.fit !== 'function') return
    try {
      cy.fit(undefined, 40)
    } catch {
      // A failed initial fit must not interrupt the simulation.
    }
    if (fitTimerRef.current !== null) window.clearTimeout(fitTimerRef.current)
    fitTimerRef.current = window.setTimeout(() => {
      fitTimerRef.current = null
      const current = cyRef.current
      if (!current || typeof current.fit !== 'function') return
      try {
        current.fit(undefined, 40)
      } catch {
        // Keep the current viewport if the second fit fails.
      }
    }, 1200)
  }, [])

  const runStaticFallback = useCallback(
    (cy: cytoscape.Core) => {
      try {
        cy.layout({ name: 'breadthfirst', directed: false, padding: 40, animate: false }).run()
      } catch {
        // Keep the loaded graph and its fallback table visible.
      }
      setPhysicsState('frozen')
    },
    [setPhysicsState],
  )

  const runEngine = useCallback(
    (reheat = false) => {
      const cy = cyRef.current
      if (!cy || staticLayout) return
      layoutRef.current?.stop()
      layoutRef.current = null
      const token = ++runTokenRef.current
      setEngineNotice(null)
      setActiveEngine(engine)

      if (reducedMotion && !finiteEngine) {
        runStaticFallback(cy)
        return
      }

      try {
        if (engine === 'fcose' && !fcoseAvailable) {
          throw new Error('fCoSE is not registered')
        }
        const layout = cy.layout(
          forceEngineOptions(engine, variant, nodeCount, cy.height(), {
            randomize: reheat,
            reducedMotion,
          }),
        )
        if (finiteEngine) {
          layout.one('layoutstop', () => {
            if (token !== runTokenRef.current) return
            setPhysicsState('complete')
            try {
              cy.fit(undefined, 40)
            } catch {
              // Keep the completed layout viewport if the fit fails.
            }
          })
        }
        setPhysicsState('running')
        layout.run()
        layoutRef.current = layout
        if (variant === 'overview' && engine === 'd3-force' && !reheat) fitOverview()
      } catch {
        layoutRef.current = null
        if (engine !== 'd3-force') {
          setEngineNotice(`The ${engineLabel(engine)} engine is unavailable. Using d3-force.`)
          setActiveEngine('d3-force')
          try {
            const fallback = cy.layout(
              d3ForceOptions(variant, nodeCount, cy.height(), { randomize: reheat }),
            )
            fallback.run()
            layoutRef.current = fallback
            setPhysicsState('running')
            if (variant === 'overview' && !reheat) fitOverview()
            return
          } catch {
            layoutRef.current = null
          }
        }
        setActiveEngine('d3-force')
        runStaticFallback(cy)
      }
    },
    [
      engine,
      finiteEngine,
      fitOverview,
      nodeCount,
      reducedMotion,
      runStaticFallback,
      setPhysicsState,
      staticLayout,
      variant,
    ],
  )
  const runEngineRef = useRef(runEngine)

  useEffect(() => {
    runEngineRef.current = runEngine
  }, [runEngine])

  const freeze = useCallback(() => {
    layoutRef.current?.stop()
    layoutRef.current = null
    runTokenRef.current += 1
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
        layout: { name: 'preset', fit: staticLayout },
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

    if (staticLayout) {
      physicsRef.current = 'frozen'
    } else {
      runEngineRef.current()
    }

    let wasRunning = !staticLayout
    const onVisibility = () => {
      if (document.hidden) {
        wasRunning = physicsRef.current === 'running'
        freeze()
      } else if (wasRunning) {
        runEngineRef.current()
        wasRunning = false
      }
    }
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      if (fitTimerRef.current !== null) {
        window.clearTimeout(fitTimerRef.current)
        fitTimerRef.current = null
      }
      runTokenRef.current += 1
      cy.removeListener('select', 'node, edge', onSelectEvent)
      cy.removeListener('unselect', 'node, edge', onUnselectEvent)
      layoutRef.current?.stop()
      cy.destroy()
      cyRef.current = null
      layoutRef.current = null
    }
  }, [freeze, graph, staticLayout])

  const engineRef = useRef(engine)
  useEffect(() => {
    if (engineRef.current === engine) return
    engineRef.current = engine
    runEngineRef.current()
  }, [engine])

  useEffect(() => {
    const container = containerRef.current
    if (!container || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => {
      const cy = cyRef.current
      if (!cy || typeof cy.resize !== 'function') return
      try {
        cy.resize()
      } catch {
        // Keep the current graph if a resize is not available.
      }
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy || typeof cy.nodes !== 'function') return
    const term = highlightSearch.trim().toLocaleLowerCase()
    cy.nodes().forEach((node) => {
      const producer = node.hasClass('node-producer')
      const label = String(node.data('label') ?? '').toLocaleLowerCase()
      node.toggleClass('searchable-producer', producer && term.length > 0)
      node.toggleClass('search-match', producer && term.length > 0 && label.includes(term))
    })
  }, [graph, highlightSearch])

  const statusText = staticLayout
    ? 'Static layout. Drag a node to inspect the network.'
    : activeFinite
      ? displayPhysics === 'running'
        ? `${engineLabel(activeEngine)} layout running. Drag a node to inspect the network.`
        : displayPhysics === 'complete'
          ? `${engineLabel(activeEngine)} layout complete. Drag a node to inspect the network.`
          : `Layout frozen · ${engineLabel(activeEngine)}. Drag a node to move the network.`
      : `${displayPhysics === 'running' ? 'Physics running' : 'Layout frozen'} · d3-force. Drag a node to move the network.`

  return (
    <section className="producer-graph" data-testid="producer-graph" aria-labelledby="producer-graph-heading">
      <div className="graph-toolbar">
        <h2 id="producer-graph-heading">Network</h2>
        <div className="graph-actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={freeze}
            disabled={staticLayout || displayPhysics === 'frozen' || displayPhysics === 'complete'}
          >
            Freeze layout
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => runEngine(false)}
            disabled={staticLayout || displayPhysics === 'running'}
          >
            Resume physics
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => runEngine(true)}
            disabled={staticLayout}
          >
            Reheat
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        className={`graph-canvas producer-graph-canvas${
          variant === 'overview' ? ' overview-graph-canvas' : ''
        }`}
        role="img"
        aria-label={
          variant === 'overview' ? 'Global producer network graph' : 'Producer network graph'
        }
        data-testid="producer-graph-canvas"
      />
      {engineNotice ? (
        <p className="async-state" role="status">
          {engineNotice}
        </p>
      ) : null}
      <p className="graph-meta" role="status">
        {statusText}
      </p>
    </section>
  )
}
