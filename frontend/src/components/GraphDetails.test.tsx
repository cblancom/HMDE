import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import type { ProducerGraphEdge, ProducerGraphNode } from '../api/producerGraph'
import { GraphDetails } from './GraphDetails'

const node: ProducerGraphNode = {
  id: 'album-1',
  type: 'album',
  label: 'Iron Maiden',
  roles: ['album'],
  attributes: { year: 1980, band_name: 'Iron Maiden' },
}
const producer: ProducerGraphNode = {
  id: 'producer-1',
  type: 'producer',
  label: 'Martin Birch',
  roles: ['producer'],
  attributes: { artist_type: 'person' },
}
const edge: ProducerGraphEdge = {
  source: 'producer-1',
  target: 'album-1',
  layer: 'producer_album',
  role: 'producer',
  weight: 1,
  support_ratio: 1,
  supporting_recordings: 9,
  album_recordings: 9,
  album_count: null,
  evidence: {},
}

describe('GraphDetails', () => {
  it('shows empty, node and edge details', () => {
    const { rerender } = render(
      <MemoryRouter><GraphDetails node={null} edge={null} nodes={[]} /></MemoryRouter>,
    )
    expect(screen.getByText(/Select a node or edge/)).toBeInTheDocument()

    rerender(
      <MemoryRouter><GraphDetails node={node} edge={null} nodes={[producer, node]} /></MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Iron Maiden' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open album details' })).toHaveAttribute(
      'href',
      '/albums/album-1',
    )

    rerender(
      <MemoryRouter><GraphDetails node={null} edge={edge} nodes={[producer, node]} /></MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Edge' })).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
  })
})
