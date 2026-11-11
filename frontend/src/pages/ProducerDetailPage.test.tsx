import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { mockFetchRoutes } from '../test/fetch'
import { renderWithProviders } from '../test/render'
import { ProducerDetailPage } from './ProducerDetailPage'

const producer = {
  id: 'producer-1',
  mbid: 'mbid-producer-1',
  name: 'Martin Birch',
  country: 'GB',
  artist_type: 'person',
  album_count: 17,
  band_count: 5,
  self_produced_albums: 0,
  betweenness: 0.125,
  community_key: 'community-001',
  top_albums: [
    { album_id: 'album-1', title: 'Iron Maiden', band_name: 'Iron Maiden', year: 1980, role: 'producer', support_ratio: 1 },
  ],
  top_bands: [
    { band_id: 'band-1', name: 'Iron Maiden', album_count: 3, first_year: 1980, last_year: 1982 },
  ],
  meta: {
    analysis_run_id: 'run-1',
    analysis_version: 'net-test',
    dataset_version: 'mb-test',
    taxonomy_version: '0.2.0',
    graph_version: '0.1.0',
    finished_at: '2026-11-10T00:00:00Z',
  },
}

function renderProducer(route = '/producers/producer-1') {
  return renderWithProviders(
    <Routes><Route path="/producers/:producerId" element={<ProducerDetailPage />} /></Routes>,
    { route },
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ProducerDetailPage', () => {
  it('renders metrics, top albums and bands', async () => {
    mockFetchRoutes({ '/api/v1/producers/producer-1': { body: producer } })
    renderProducer()

    expect(await screen.findByRole('heading', { name: 'Martin Birch', level: 1 })).toBeInTheDocument()
    expect(screen.getByText('community-001')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open graph' })).toHaveAttribute(
      'href',
      '/producers/producer-1/graph',
    )
    const links = await screen.findAllByRole('link', { name: 'Iron Maiden' })
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      '/albums/album-1',
      '/bands/band-1',
    ])
  })

  it('shows not-found state', async () => {
    mockFetchRoutes({ '/api/v1/producers/missing': { status: 404, body: {} } })
    renderProducer('/producers/missing')
    expect(await screen.findByText('Producer not found.')).toBeInTheDocument()
  })
})
