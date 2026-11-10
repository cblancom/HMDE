import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'

afterEach(() => {
  vi.unstubAllGlobals()
})

function mockShell() {
  return mockFetchRoutes({
    '/health': { body: { status: 'ok', database: 'ok' } },
    '/api/v1/taxonomy': { body: { version: '0.2.0', nodes: [] } },
    '/api/v1/bands': { body: { items: [], total: 0, limit: 20, offset: 0 } },
    '/api/v1/albums': { body: { items: [], total: 0, limit: 20, offset: 0 } },
    '/api/v1/search': { body: { query: 'iron', bands: [], albums: [], producers: [] } },
  })
}

describe('AppShell', () => {
  it('navigates between primary sections and submits global search', async () => {
    mockShell()
    renderWithProviders(<App />, { route: '/albums' })

    expect(screen.getByRole('heading', { name: 'Albums' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute(
      'href',
      '#main-content',
    )
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content')
    expect(screen.getByRole('link', { name: 'Bands' })).toHaveAttribute('href', '/bands')
    expect(screen.getByRole('link', { name: 'Producers' })).toHaveAttribute('href', '/producers')

    fireEvent.change(screen.getByLabelText('Search the archive'), {
      target: { value: 'iron' },
    })
    const searchForm = screen.getByLabelText('Search the archive').closest('form')
    expect(searchForm).not.toBeNull()
    fireEvent.click(within(searchForm as HTMLElement).getByRole('button', { name: 'Search' }))

    expect(await screen.findByRole('heading', { name: 'Search' })).toBeInTheDocument()
  })
})
