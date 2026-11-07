import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ApiStatus, type ApiState } from './ApiStatus'

const cases: Array<[ApiState, RegExp]> = [
  [{ status: 'loading' }, /checking api status/i],
  [{ status: 'available' }, /api available/i],
  [{ status: 'degraded' }, /api degraded/i],
  [{ status: 'unavailable' }, /api unavailable/i],
]

describe('ApiStatus', () => {
  it.each(cases)('renders the %s state', (state, expected) => {
    render(<ApiStatus state={state} />)

    expect(screen.getByRole('status')).toHaveTextContent(expected)
  })
})
