import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { BandGraph } from './BandGraph'

const { cytoscapeMock, destroyMock } = vi.hoisted(() => {
  const destroy = vi.fn()
  const factory = vi.fn(() => ({ destroy }))
  return { cytoscapeMock: factory, destroyMock: destroy }
})

vi.mock('cytoscape', () => ({ default: cytoscapeMock }))

const graph = {
  nodes: [
    { id: 'band-1', label: 'Iron Maiden', type: 'band' as const },
    { id: 'artist-1', label: 'Martin Birch', type: 'producer' as const },
  ],
  edges: [
    {
      source: 'band-1',
      target: 'artist-1',
      type: 'produced' as const,
      role: 'producer' as const,
      album_count: 2,
      albums: ['Iron Maiden', 'Killers'],
    },
  ],
  meta: { fixture_version: 'e2-v0.1.0' },
}

beforeEach(() => {
  cytoscapeMock.mockClear()
  destroyMock.mockClear()
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('BandGraph', () => {
  it('renders the graph, legend and accessible fallback table', () => {
    render(<BandGraph graph={graph} />)

    expect(screen.getByRole('heading', { name: 'Producer graph' })).toBeInTheDocument()
    expect(screen.getByTestId('band-graph')).toHaveAttribute(
      'aria-label',
      'Producer graph for Iron Maiden',
    )
    expect(screen.getByRole('list', { name: 'Graph legend' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Producer graph fallback' })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'Martin Birch' })).toBeInTheDocument()
    expect(
      screen.getByRole('cell', { name: 'Iron Maiden, Killers' }),
    ).toBeInTheDocument()
    expect(cytoscapeMock).toHaveBeenCalledTimes(1)
  })

  it('destroys the Cytoscape instance on unmount', () => {
    const { unmount } = render(<BandGraph graph={graph} />)

    expect(destroyMock).not.toHaveBeenCalled()
    unmount()
    expect(destroyMock).toHaveBeenCalledTimes(1)
  })

  it('shows an empty state when there are no producer credits', () => {
    render(
      <BandGraph
        graph={{
          nodes: [{ id: 'band-1', label: 'No Credit Band', type: 'band' }],
          edges: [],
          meta: { fixture_version: 'e2-v0.1.0' },
        }}
      />,
    )

    expect(
      screen.getByText(/No documented producer credits/),
    ).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})
