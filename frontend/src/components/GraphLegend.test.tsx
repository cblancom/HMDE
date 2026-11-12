import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { GraphLegend } from './GraphLegend'

describe('GraphLegend', () => {
  it('explains node, edge and support encodings', () => {
    render(<GraphLegend />)
    expect(screen.getByRole('list', { name: 'Graph legend' })).toBeInTheDocument()
    expect(screen.getByText(/Dashed edges/)).toBeInTheDocument()
    expect(screen.getByText('1960 to 2026')).toBeInTheDocument()
  })

  it('shows the dynamic overview year range', () => {
    render(<GraphLegend yearRange={{ min: 1985, max: 1991 }} />)
    expect(screen.getByText('1985 to 1991')).toBeInTheDocument()
    expect(screen.queryByText('1960 to 2026')).not.toBeInTheDocument()
  })

  it('hides the year item when the overview has no albums', () => {
    render(<GraphLegend yearRange={null} />)
    expect(screen.queryByText('1960 to 2026')).not.toBeInTheDocument()
    expect(screen.queryByText(/^\d{4} to \d{4}$/)).not.toBeInTheDocument()
  })
})
