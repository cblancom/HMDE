import { useQuery } from '@tanstack/react-query'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router'

import { getProducers, type ProducerSort } from '../api/producers'
import { queryKeys } from '../api/queryKeys'
import { AsyncState } from '../components/AsyncState'
import { Pagination } from '../components/Pagination'
import { PeriodFilter } from '../components/PeriodFilter'
import { ProducerList } from '../components/ProducerList'
import { TaxonomySelect } from '../components/TaxonomySelect'

const PAGE_SIZE = 20

export function ProducersPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const subgenre = searchParams.get('subgenre') ?? ''
  const decade = searchParams.get('decade') ?? ''
  const sort = (searchParams.get('sort') as ProducerSort | null) ?? 'album_count'
  const offset = Number(searchParams.get('offset') ?? 0)

  const filters = {
    q: q || undefined,
    subgenre: subgenre || undefined,
    decade: decade || undefined,
    sort,
    order: 'desc' as const,
    limit: PAGE_SIZE,
    offset,
  }
  const producersQuery = useQuery({
    queryKey: queryKeys.producers(filters),
    queryFn: () => getProducers(filters),
  })

  function updateFilters(next: { q: string; subgenre: string; decade: string; sort: ProducerSort }) {
    const params = new URLSearchParams()
    if (next.q) params.set('q', next.q)
    if (next.subgenre) params.set('subgenre', next.subgenre)
    if (next.decade) params.set('decade', next.decade)
    if (next.sort !== 'album_count') params.set('sort', next.sort)
    setSearchParams(params)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const field = event.currentTarget.elements.namedItem('q')
    const search = field instanceof HTMLInputElement ? field.value.trim() : ''
    updateFilters({ q: search, subgenre, decade, sort })
  }

  const hasFilters = Boolean(q || subgenre || decade || sort !== 'album_count')

  return (
    <section className="page" aria-labelledby="producers-heading">
      <header className="page-header">
        <h1 id="producers-heading">Producers</h1>
        <p>See who shaped the records, how often they worked and where they connect.</p>
      </header>

      <form className="filters" role="search" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="producer-search">Search producers</label>
          <input id="producer-search" name="q" type="search" defaultValue={q} placeholder="Martin Birch" />
        </div>
        <TaxonomySelect value={subgenre} onChange={(value) => updateFilters({ q, subgenre: value, decade, sort })} />
        <PeriodFilter value={decade} onChange={(value) => updateFilters({ q, subgenre, decade: value, sort })} />
        <div className="field">
          <label htmlFor="producer-sort">Rank by</label>
          <select
            id="producer-sort"
            value={sort}
            onChange={(event) => updateFilters({ q, subgenre, decade, sort: event.target.value as ProducerSort })}
          >
            <option value="album_count">Albums</option>
            <option value="band_count">Bands</option>
            <option value="betweenness">Betweenness</option>
            <option value="name">Name</option>
          </select>
        </div>
        <div className="filter-actions">
          <button type="submit" className="button">Search</button>
          {hasFilters ? (
            <button type="button" className="button button--secondary" onClick={() => setSearchParams(new URLSearchParams())}>
              Clear filters
            </button>
          ) : null}
        </div>
      </form>

      {producersQuery.isPending ? <AsyncState status="loading" message="Loading producers…" /> : null}
      {producersQuery.isError ? (
        <AsyncState status="error" message="Could not load producers." onRetry={() => void producersQuery.refetch()} />
      ) : null}
      {producersQuery.isSuccess ? (
        producersQuery.data.items.length === 0 ? (
          <AsyncState status="empty" message="No producers match these filters." />
        ) : (
          <>
            <p className="result-count" role="status">
              {producersQuery.data.total} {producersQuery.data.total === 1 ? 'producer' : 'producers'}
            </p>
            <ProducerList items={producersQuery.data.items} />
            <Pagination total={producersQuery.data.total} limit={producersQuery.data.limit} offset={producersQuery.data.offset} />
          </>
        )
      ) : null}
    </section>
  )
}
