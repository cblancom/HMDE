import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { SearchPage } from './SearchPage'

const results = {
  query: 'iron',
  bands: [{ id: 'band-1', name: 'Iron Maiden', subgenre: 'Heavy Metal' }],
  albums: [{ id: 'album-1', title: 'Iron Maiden', band_name: 'Iron Maiden', year: 1980 }],
  producers: [{ id: 'producer-1', name: 'Martin Birch' }],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SearchPage', () => {
  it('prompts before a query and renders grouped results after one', async () => {
    mockFetchRoutes({ '/api/v1/search': { body: results } })
    const { unmount } = renderWithProviders(<SearchPage />, { route: '/search' })
    expect(screen.getByText('Type a query to search the archive.')).toBeInTheDocument()
    unmount()

    renderWithProviders(<SearchPage />, { route: '/search?q=iron' })
    const ironLinks = await screen.findAllByRole('link', { name: 'Iron Maiden' })
    expect(ironLinks.map((link) => link.getAttribute('href'))).toEqual([
      '/bands/band-1',
      '/albums/album-1',
    ])
    expect(screen.getByRole('link', { name: 'Martin Birch' })).toHaveAttribute(
      'href',
      '/producers/producer-1',
    )
    expect(screen.getByRole('heading', { name: 'Albums' })).toBeInTheDocument()
  })
})
