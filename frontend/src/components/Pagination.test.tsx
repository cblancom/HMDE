import { fireEvent, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Route, Routes, useLocation } from 'react-router'

import { Pagination } from './Pagination'
import { renderWithProviders } from '../test/render'

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.search}</output>
}

function renderPagination(route: string, offset = 20) {
  return renderWithProviders(
    <Routes>
      <Route
        path="/bands"
        element={
          <>
            <Pagination total={65} limit={20} offset={offset} />
            <LocationProbe />
          </>
        }
      />
    </Routes>,
    { route },
  )
}

describe('Pagination', () => {
  it('preserves filters and updates the offset', () => {
    renderPagination('/bands?q=iron&offset=20')

    expect(screen.getByText('Page 2 of 4')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByTestId('location')).toHaveTextContent('?q=iron&offset=40')
  })

  it('disables previous on the first page', () => {
    renderPagination('/bands?q=iron', 0)
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  })
})
