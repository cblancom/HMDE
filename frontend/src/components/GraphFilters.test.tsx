import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { GraphFilters } from './GraphFilters'

describe('GraphFilters', () => {
  it('emits role changes and disables unsupported filters', () => {
    const onChange = vi.fn()
    render(
      <GraphFilters
        filters={{ role: 'all', decade: '', subgenre: '' }}
        decades={['1980s']}
        subgenres={['heavy-metal']}
        supportsDecade={false}
        supportsSubgenre={false}
        onChange={onChange}
      />,
    )
    expect(screen.getByLabelText('Decade')).toBeDisabled()
    expect(screen.getByLabelText('Subgenre')).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'co-producer' } })
    expect(onChange).toHaveBeenCalledWith({ role: 'co-producer', decade: '', subgenre: '' })
  })
})
