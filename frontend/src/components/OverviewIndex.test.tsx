import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { OverviewIndex } from './OverviewIndex'

const producers = [
  { id: 'producer-1', label: 'Alice Producer', count: 2 },
  { id: 'producer-2', label: 'Bob Producer', count: 1 },
]
const bands = [
  { id: 'band-1', label: 'Shared Band', count: 5 },
  { id: 'band-2', label: 'Other Band', count: 2 },
]

function renderIndex(overrides: Partial<Parameters<typeof OverviewIndex>[0]> = {}) {
  return render(
    <MemoryRouter>
      <OverviewIndex producers={producers} bands={bands} {...overrides} />
    </MemoryRouter>,
  )
}

describe('OverviewIndex', () => {
  it('shows both lists with counts, links and order', () => {
    renderIndex()

    expect(screen.getByRole('complementary', { name: 'Network index' })).toBeInTheDocument()
    expect(screen.getByText('Producers')).toBeInTheDocument()
    expect(screen.getByText('Bands')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Producers'))
    fireEvent.click(screen.getByText('Bands'))
    const producerLinks = screen.getAllByRole('link').slice(0, 2)
    expect(producerLinks.map((link) => link.textContent)).toEqual([
      'Alice Producer',
      'Bob Producer',
    ])
    expect(producerLinks[0]).toHaveAttribute('href', '/producers/producer-1')

    const bandLinks = screen.getAllByRole('link').slice(2)
    expect(bandLinks.map((link) => link.textContent)).toEqual(['Shared Band', 'Other Band'])
    expect(bandLinks[0]).toHaveAttribute('href', '/bands/band-1')
  })

  it('collapses and expands a section from its summary', () => {
    renderIndex()
    const details = screen.getByText('Producers').closest('details')
    expect(details).not.toHaveAttribute('open')

    fireEvent.click(screen.getByText('Producers'))
    expect(details).toHaveAttribute('open')

    fireEvent.click(screen.getByText('Producers'))
    expect(details).not.toHaveAttribute('open')
  })

  it('renders the band loading state', () => {
    renderIndex({ bandsLoading: true })
    expect(screen.getByText('Loading bands…')).toBeInTheDocument()
  })

  it('renders the band retry state', () => {
    const onRetryBands = vi.fn()
    renderIndex({ bandsError: true, onRetryBands })
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetryBands).toHaveBeenCalled()
  })
})
