import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { GraphFallbackTable } from './GraphFallbackTable'

describe('GraphFallbackTable', () => {
  it('lists nodes and edges as accessible tables', () => {
    render(
      <GraphFallbackTable
        nodes={[{ id: 'album-1', label: 'Iron Maiden', type: 'album', year: 1980, detail: 'Iron Maiden, 1980' }]}
        edges={[{
          id: 'edge-1', source: 'producer-1', target: 'album-1',
          sourceLabel: 'Martin Birch', targetLabel: 'Iron Maiden',
          role: 'producer', support: '100%', albumCount: null,
        }]}
      />,
    )
    expect(screen.getByText('View the network as tables')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Loaded graph nodes' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Loaded graph edges' })).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: 'Martin Birch' })).toBeInTheDocument()
  })
})
