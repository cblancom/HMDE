import { fireEvent, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '../test/render'
import {
  ProducerOverviewControls,
  type OverviewDisplayOptions,
  type OverviewOptions,
} from './ProducerOverviewControls'

const options: OverviewOptions = {
  view: 'bands',
  producerLimit: 0,
  bandLimit: 0,
  albumLimit: 500,
  producerSort: 'album_count',
  order: 'desc',
  decade: '',
  subgenre: '',
  layout: 'force',
  engine: 'd3-force',
}

const display: OverviewDisplayOptions = {
  role: 'all',
  hideIsolated: false,
  producerSearch: '',
}

function renderControls(overrides: Partial<OverviewOptions> = {}) {
  const onOptionsChange = vi.fn()
  renderWithProviders(
    <ProducerOverviewControls
      options={{ ...options, ...overrides }}
      display={display}
      onOptionsChange={onOptionsChange}
      onDisplayChange={vi.fn()}
      onReset={vi.fn()}
    />,
  )
  return onOptionsChange
}

describe('ProducerOverviewControls', () => {
  it('shows the force engine group with d3-force selected by default', () => {
    renderControls()

    expect(screen.getByText('Force engine')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'd3-force' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: 'CoSE' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.getByRole('button', { name: 'fCoSE' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  it('reports engine changes through the options callback', () => {
    const onOptionsChange = renderControls()

    fireEvent.click(screen.getByRole('button', { name: 'CoSE' }))
    expect(onOptionsChange).toHaveBeenCalledWith({ ...options, engine: 'cose' })

    fireEvent.click(screen.getByRole('button', { name: 'fCoSE' }))
    expect(onOptionsChange).toHaveBeenCalledWith({ ...options, engine: 'fcose' })
  })

  it('reports band and album limit changes', () => {
    const onOptionsChange = renderControls({ bandLimit: 100, albumLimit: 500 })

    fireEvent.change(screen.getByLabelText('Band limit'), { target: { value: '250' } })
    expect(onOptionsChange).toHaveBeenCalledWith({ ...options, bandLimit: 250, albumLimit: 500 })

    fireEvent.click(screen.getByLabelText('Album limit all'))
    expect(onOptionsChange).toHaveBeenCalledWith({ ...options, bandLimit: 100, albumLimit: 0 })
  })

  it('reports a typed producer limit on blur and supports All', () => {
    const onOptionsChange = renderControls({ producerLimit: 100 })
    const input = screen.getByRole('spinbutton', { name: 'Producers' })

    fireEvent.change(input, { target: { value: '137' } })
    expect(onOptionsChange).not.toHaveBeenCalled()
    fireEvent.blur(input)
    expect(onOptionsChange).toHaveBeenCalledWith({ ...options, producerLimit: 137 })

    fireEvent.change(input, { target: { value: '1500' } })
    fireEvent.blur(input)
    expect(onOptionsChange).toHaveBeenCalledWith({ ...options, producerLimit: 1000 })

    fireEvent.click(screen.getByRole('checkbox', { name: 'Producers all' }))
    expect(onOptionsChange).toHaveBeenCalledWith({ ...options, producerLimit: 0 })
  })

  it('disables the engine group outside Force', () => {
    renderControls({ layout: 'community', engine: 'fcose' })

    for (const name of ['d3-force', 'CoSE', 'fCoSE']) {
      expect(screen.getByRole('button', { name })).toBeDisabled()
    }
    expect(screen.getByText('Available when Layout is Force.')).toBeInTheDocument()
  })
})
