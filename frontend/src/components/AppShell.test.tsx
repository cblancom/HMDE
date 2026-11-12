import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'

beforeEach(() => {
  window.localStorage.clear()
})

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
    '/api/v1/graph/producers': { status: 500, body: {} },
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
    expect(screen.getByRole('link', { name: 'Graph' })).toHaveAttribute('href', '/graph')

    fireEvent.change(screen.getByLabelText('Search the archive'), {
      target: { value: 'iron' },
    })
    const searchForm = screen.getByLabelText('Search the archive').closest('form')
    expect(searchForm).not.toBeNull()
    fireEvent.click(within(searchForm as HTMLElement).getByRole('button', { name: 'Search' }))

    expect(await screen.findByRole('heading', { name: 'Search' })).toBeInTheDocument()
  })

  it('collapses the navigation rail and persists the preference', () => {
    mockShell()
    const { unmount } = renderWithProviders(<App />, { route: '/albums' })

    const collapse = screen.getByRole('button', { name: 'Collapse navigation' })
    expect(collapse).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(collapse)
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.getByRole('main').closest('.app-shell')).toHaveClass(
      'app-shell--rail-collapsed',
    )
    expect(window.localStorage.getItem('hmde:rail-collapsed')).toBe('true')

    unmount()
    renderWithProviders(<App />, { route: '/bands' })
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toBeInTheDocument()
  })

  it('starts with the rail collapsed on /graph without a stored preference', async () => {
    mockShell()
    renderWithProviders(<App />, { route: '/graph' })

    expect(await screen.findByRole('button', { name: 'Expand navigation' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.getByRole('main').closest('.app-shell')).toHaveClass(
      'app-shell--rail-collapsed',
    )
  })
})
