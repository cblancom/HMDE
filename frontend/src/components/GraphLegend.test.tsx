import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { GraphLegend } from './GraphLegend'

describe('GraphLegend', () => {
  it('explains node, edge and support encodings', () => {
    render(<GraphLegend />)
    expect(screen.getByRole('list', { name: 'Graph legend' })).toBeInTheDocument()
    expect(screen.getByText(/Dashed edges/)).toBeInTheDocument()
  })
})
