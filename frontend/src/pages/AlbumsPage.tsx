import { useQuery } from '@tanstack/react-query'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router'

import { getAlbums } from '../api/albums'
import { queryKeys } from '../api/queryKeys'
import { AlbumList } from '../components/AlbumList'
import { AsyncState } from '../components/AsyncState'
import { Pagination } from '../components/Pagination'
import { PeriodFilter } from '../components/PeriodFilter'
import { TaxonomySelect } from '../components/TaxonomySelect'

const PAGE_SIZE = 20

export function AlbumsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const subgenre = searchParams.get('subgenre') ?? ''
  const decade = searchParams.get('decade') ?? ''
  const bandId = searchParams.get('band_id') ?? ''
  const producerId = searchParams.get('producer_id') ?? ''
  const offset = Number(searchParams.get('offset') ?? 0)

  const filters = {
    q: q || undefined,
    bandId: bandId || undefined,
    producerId: producerId || undefined,
    subgenre: subgenre || undefined,
    decade: decade || undefined,
    limit: PAGE_SIZE,
    offset,
  }
  const albumsQuery = useQuery({
    queryKey: queryKeys.albums(filters),
    queryFn: () => getAlbums(filters),
  })

  function updateFilters(next: { q: string; subgenre: string; decade: string }) {
    const params = new URLSearchParams()
    if (next.q) params.set('q', next.q)
    if (next.subgenre) params.set('subgenre', next.subgenre)
    if (next.decade) params.set('decade', next.decade)
    if (bandId) params.set('band_id', bandId)
    if (producerId) params.set('producer_id', producerId)
    setSearchParams(params)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const field = event.currentTarget.elements.namedItem('q')
    const search = field instanceof HTMLInputElement ? field.value.trim() : ''
    updateFilters({ q: search, subgenre, decade })
  }

  const hasFilters = Boolean(q || subgenre || decade || bandId || producerId)

  return (
    <section className="page" aria-labelledby="albums-heading">
      <header className="page-header">
        <h1 id="albums-heading">Albums</h1>
        <p>Trace records through their bands, credits and production roles.</p>
      </header>

      <form className="filters" role="search" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="album-search">Search albums</label>
          <input
            id="album-search"
            name="q"
            type="search"
            defaultValue={q}
            placeholder="Master of Puppets"
          />
        </div>
        <TaxonomySelect value={subgenre} onChange={(value) => updateFilters({ q, subgenre: value, decade })} />
        <PeriodFilter value={decade} onChange={(value) => updateFilters({ q, subgenre, decade: value })} />
        <div className="filter-actions">
          <button type="submit" className="button">Search</button>
          {hasFilters ? (
            <button type="button" className="button button--secondary" onClick={() => setSearchParams(new URLSearchParams())}>
              Clear filters
            </button>
          ) : null}
        </div>
      </form>

      {bandId || producerId ? (
        <p className="result-count" role="status">
          Filtered {bandId ? 'by band' : 'by producer'}. Clear filters to see the full album index.
        </p>
      ) : null}

      {albumsQuery.isPending ? <AsyncState status="loading" message="Loading albums…" /> : null}
      {albumsQuery.isError ? (
        <AsyncState status="error" message="Could not load albums." onRetry={() => void albumsQuery.refetch()} />
      ) : null}
      {albumsQuery.isSuccess ? (
        albumsQuery.data.items.length === 0 ? (
          <AsyncState status="empty" message="No albums match these filters." />
        ) : (
          <>
            <p className="result-count" role="status">
              {albumsQuery.data.total} {albumsQuery.data.total === 1 ? 'album' : 'albums'}
            </p>
            <AlbumList items={albumsQuery.data.items} />
            <Pagination total={albumsQuery.data.total} limit={albumsQuery.data.limit} offset={albumsQuery.data.offset} />
          </>
        )
      ) : null}
    </section>
  )
}
