import { useQuery } from '@tanstack/react-query'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router'

import { getBands } from '../api/bands'
import { queryKeys } from '../api/queryKeys'
import { AsyncState } from '../components/AsyncState'
import { BandList } from '../components/BandList'
import { Pagination } from '../components/Pagination'
import { PeriodFilter } from '../components/PeriodFilter'
import { TaxonomySelect } from '../components/TaxonomySelect'

const PAGE_SIZE = 20

export function BandsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const subgenre = searchParams.get('subgenre') ?? ''
  const decade = searchParams.get('decade') ?? ''
  const offset = Number(searchParams.get('offset') ?? 0)

  const filters = {
    q: q || undefined,
    subgenre: subgenre || undefined,
    decade: decade || undefined,
    limit: PAGE_SIZE,
    offset,
  }
  const bandsQuery = useQuery({
    queryKey: queryKeys.bands(filters),
    queryFn: () => getBands(filters),
  })

  function updateFilters(next: { q: string; subgenre: string; decade: string }) {
    const params = new URLSearchParams()
    if (next.q) {
      params.set('q', next.q)
    }
    if (next.subgenre) {
      params.set('subgenre', next.subgenre)
    }
    if (next.decade) {
      params.set('decade', next.decade)
    }
    setSearchParams(params)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const field = event.currentTarget.elements.namedItem('q')
    const search = field instanceof HTMLInputElement ? field.value.trim() : ''
    updateFilters({ q: search, subgenre, decade })
  }

  function handleSubgenreChange(value: string) {
    updateFilters({ q, subgenre: value, decade })
  }

  function handleDecadeChange(value: string) {
    updateFilters({ q, subgenre, decade: value })
  }

  function handleClear() {
    setSearchParams(new URLSearchParams())
  }

  const hasFilters = Boolean(q || subgenre || decade)

  return (
    <section className="page" aria-labelledby="bands-heading">
      <header className="page-header">
        <h1 id="bands-heading">Bands</h1>
        <p>Explore documented production relationships across the active corpus.</p>
      </header>

      <form className="filters" role="search" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="band-search">Search bands</label>
          <input
            id="band-search"
            key={q}
            name="q"
            type="search"
            defaultValue={q}
            placeholder="Iron Maiden"
          />
        </div>
        <TaxonomySelect value={subgenre} onChange={handleSubgenreChange} />
        <PeriodFilter value={decade} onChange={handleDecadeChange} />
        <div className="filter-actions">
          <button type="submit" className="button">
            Search
          </button>
          {hasFilters ? (
            <button type="button" className="button button--secondary" onClick={handleClear}>
              Clear filters
            </button>
          ) : null}
        </div>
      </form>

      {bandsQuery.isPending ? <AsyncState status="loading" message="Loading bands…" /> : null}

      {bandsQuery.isError ? (
        <AsyncState
          status="error"
          message="Could not load bands. Check that the API and fixtures are available."
          onRetry={() => void bandsQuery.refetch()}
        />
      ) : null}

      {bandsQuery.isSuccess ? (
        bandsQuery.data.items.length === 0 ? (
          <AsyncState status="empty" message="No bands match these filters." />
        ) : (
          <>
            <p className="result-count" role="status">
              {bandsQuery.data.total} {bandsQuery.data.total === 1 ? 'band' : 'bands'}
            </p>
            <BandList items={bandsQuery.data.items} />
            <Pagination
              total={bandsQuery.data.total}
              limit={bandsQuery.data.limit}
              offset={bandsQuery.data.offset}
            />
          </>
        )
      ) : null}
    </section>
  )
}
