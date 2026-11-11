import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ProducerGraphResponse } from '../api/producerGraph'
import { adaptGraph } from '../graph/adapter'
import { ProducerGraph } from './ProducerGraph'

const originalMatchMedia = window.matchMedia

const { cytoscapeMock, layoutRun, layoutStop, destroyMock, fitMock } = vi.hoisted(() => {
  const run = vi.fn()
  const stop = vi.fn()
  const destroy = vi.fn()
  const fit = vi.fn()
  const layout = vi.fn(() => ({ run, stop }))
  const cy = {
    layout,
    fit,
    on: vi.fn(),
    removeListener: vi.fn(),
    height: vi.fn(() => 720),
    destroy,
  }
  const factory = vi.fn(() => cy) as ReturnType<typeof vi.fn> & { use: ReturnType<typeof vi.fn> }
  factory.use = vi.fn()
  return {
    cytoscapeMock: factory,
    layoutRun: run,
    layoutStop: stop,
    destroyMock: destroy,
    fitMock: fit,
  }
})

vi.mock('cytoscape', () => ({ default: cytoscapeMock }))
vi.mock('cytoscape-d3-force', () => ({ default: vi.fn() }))

const response: ProducerGraphResponse = {
  nodes: [
    { id: 'producer-1', type: 'producer', label: 'Martin Birch', roles: ['producer'], attributes: { artist_type: 'person' } },
    { id: 'album-1', type: 'album', label: 'Iron Maiden', roles: ['album'], attributes: { year: 1980, band_name: 'Iron Maiden' } },
  ],
  edges: [
    {
      source: 'producer-1', target: 'album-1', layer: 'producer_album', role: 'producer',
      weight: 1, support_ratio: 1, supporting_recordings: 9, album_recordings: 9,
      album_count: null, evidence: {},
    },
  ],
  meta: {
    view: 'albums', analysis_run_id: 'run-1', analysis_version: 'net-test',
    dataset_version: 'mb-test', taxonomy_version: '0.2.0', graph_version: '0.1.0',
    truncated: false, limits: { limit: 20, depth: 1, max_nodes: 500, max_edges: 2000 },
  },
}

afterEach(() => {
  vi.unstubAllGlobals()
  if (originalMatchMedia) {
    Object.defineProperty(window, 'matchMedia', { configurable: true, writable: true, value: originalMatchMedia })
  } else {
    // jsdom does not implement matchMedia; remove the stub.
    delete (window as Window & { matchMedia?: unknown }).matchMedia
  }
})

beforeEach(() => {
  cytoscapeMock.mockClear()
  layoutRun.mockClear()
  layoutStop.mockClear()
  destroyMock.mockClear()
  fitMock.mockClear()
})

describe('ProducerGraph', () => {
  it('starts physics and supports freeze/resume/reheat', () => {
    const graph = adaptGraph(response, 'albums', { role: 'all', decade: '', subgenre: '' }, 'producer-1')
    render(<ProducerGraph graph={graph} />)

    expect(cytoscapeMock).toHaveBeenCalledTimes(1)
    expect(layoutRun).toHaveBeenCalled()
    expect(screen.getByText(/Physics running/)).toBeInTheDocument()
    const layoutOptions = (cytoscapeMock.mock.results[0]?.value as { layout: ReturnType<typeof vi.fn> }).layout.mock.calls.at(-1)?.[0]
    expect(layoutOptions).toMatchObject({ name: 'd3-force', infinite: true, fixedAfterDragging: false, ungrabifyWhileSimulating: false })
    expect(typeof layoutOptions.linkId).toBe('function')
    expect(layoutOptions.linkId({ id: 'producer-1' })).toBe('producer-1')
    expect(layoutOptions.manyBodyStrength).toBeLessThanOrEqual(-300)
    expect(layoutOptions.linkDistance).toBeGreaterThanOrEqual(180)
    expect(layoutOptions.linkDistance).toBeLessThanOrEqual(300)
    expect(layoutOptions.collideStrength).toBeGreaterThanOrEqual(0.8)
    expect(layoutOptions.collideRadius({ type: 'producer' })).toBe(22)
    expect(layoutOptions.collideRadius({ type: 'album' })).toBe(28)
    expect(layoutOptions.collideRadius({ type: 'band' })).toBe(34)

    fireEvent.click(screen.getByRole('button', { name: 'Freeze layout' }))
    expect(layoutStop).toHaveBeenCalled()
    expect(screen.getByText(/Layout frozen/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Resume physics' }))
    expect(layoutRun).toHaveBeenCalledTimes(2)

    fireEvent.click(screen.getByRole('button', { name: 'Reheat' }))
    expect(layoutRun).toHaveBeenCalledTimes(3)
  })


  it('uses a compact overview preset and fits the initial network', () => {
    const graph = adaptGraph(response, 'albums', { role: 'all', decade: '', subgenre: '' }, 'producer-1')
    render(<ProducerGraph graph={graph} variant="overview" />)

    const layoutOptions = (cytoscapeMock.mock.results[0]?.value as { layout: ReturnType<typeof vi.fn> }).layout.mock.calls.at(-1)?.[0]
    expect(layoutOptions.manyBodyStrength).toBeGreaterThan(-100)
    expect(layoutOptions.manyBodyStrength).toBeLessThan(0)
    expect(layoutOptions.linkDistance).toBeLessThan(180)
    expect(layoutOptions.collideStrength).toBeLessThan(0.8)
    expect(layoutOptions.collideRadius({ type: 'producer' })).toBe(8)
    expect(layoutOptions.collideRadius({ type: 'album' })).toBe(7)
    expect(layoutOptions.collideRadius({ type: 'band' })).toBe(10)
    expect(fitMock).toHaveBeenCalled()
    expect(screen.getByLabelText('Global producer network graph')).toBeInTheDocument()
  })

  it('uses infinite d3-force options and starts frozen under reduced motion', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn(() => ({ matches: true, media: '', addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(), onchange: null })),
    })
    const graph = adaptGraph(response, 'albums', { role: 'all', decade: '', subgenre: '' }, 'producer-1')
    render(<ProducerGraph graph={graph} />)
    expect(screen.getByText(/Layout frozen/)).toBeInTheDocument()
    const layoutMock = (cytoscapeMock.mock.results[0]?.value as { layout: ReturnType<typeof vi.fn> }).layout
    const layoutOptions = layoutMock.mock.calls.at(-1)?.[0]
    expect(layoutOptions).toMatchObject({ name: 'breadthfirst', animate: false })
    vi.unstubAllGlobals()
  })


  it('falls back to a static layout when physics fails', () => {
    layoutRun.mockImplementationOnce(() => {
      throw new Error('node not found: producer-1')
    })
    const graph = adaptGraph(response, 'albums', { role: 'all', decade: '', subgenre: '' }, 'producer-1')
    render(<ProducerGraph graph={graph} />)

    expect(screen.getByText(/Layout frozen/)).toBeInTheDocument()
    const layoutMock = (cytoscapeMock.mock.results[0]?.value as { layout: ReturnType<typeof vi.fn> }).layout
    expect(layoutMock.mock.calls.at(-1)?.[0]).toMatchObject({ name: 'breadthfirst', animate: false })
  })

  it('pauses physics when the document becomes hidden', () => {
    const graph = adaptGraph(response, 'albums', { role: 'all', decade: '', subgenre: '' }, 'producer-1')
    render(<ProducerGraph graph={graph} />)
    Object.defineProperty(document, 'hidden', { configurable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(layoutStop).toHaveBeenCalled()
    Object.defineProperty(document, 'hidden', { configurable: true, value: false })
  })

  it('destroys the graph on unmount', () => {
    const graph = adaptGraph(response, 'albums', { role: 'all', decade: '', subgenre: '' }, 'producer-1')
    const { unmount } = render(<ProducerGraph graph={graph} />)
    unmount()
    expect(destroyMock).toHaveBeenCalled()
  })
})
