import { useQuery } from '@tanstack/react-query'
import type { ChangeEvent, FormEvent } from 'react'
import { useSearchParams } from 'react-router'

import { getBands } from '../api/bands'
import { AsyncState } from '../components/AsyncState'
import { BandList } from '../components/BandList'

const SUBGENRES = [
  { code: 'heavy-metal', name: 'Heavy Metal' },
  { code: 'thrash-metal', name: 'Thrash Metal' },
  { code: 'death-metal', name: 'Death Metal' },
  { code: 'black-metal', name: 'Black Metal' },
  { code: 'power-metal', name: 'Power Metal' },
  { code: 'doom-metal', name: 'Doom Metal' },
  { code: 'progressive-metal', name: 'Progressive Metal' },
]

export function BandsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const subgenre = searchParams.get('subgenre') ?? ''

  const bandsQuery = useQuery({
    queryKey: ['bands', { q, subgenre }],
    queryFn: () => getBands({ q: q || undefined, subgenre: subgenre || undefined }),
  })

  function updateFilters(next: { q: string; subgenre: string }) {
    const params = new URLSearchParams()
    if (next.q) {
      params.set('q', next.q)
    }
    if (next.subgenre) {
      params.set('subgenre', next.subgenre)
    }
    setSearchParams(params)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const field = event.currentTarget.elements.namedItem('q')
    const search = field instanceof HTMLInputElement ? field.value.trim() : ''
    updateFilters({ q: search, subgenre })
  }

  function handleSubgenreChange(event: ChangeEvent<HTMLSelectElement>) {
    updateFilters({ q, subgenre: event.target.value })
  }

  function handleClear() {
    setSearchParams(new URLSearchParams())
  }

  const hasFilters = Boolean(q || subgenre)

  return (
    <section className="page" aria-labelledby="bands-heading">
      <header className="page-header">
        <p className="eyebrow">E2 seed dataset</p>
        <h1 id="bands-heading">Bands</h1>
        <p>Explore documented production relationships across the seed dataset.</p>
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
        <div className="field">
          <label htmlFor="band-subgenre">Subgenre</label>
          <select
            id="band-subgenre"
            name="subgenre"
            value={subgenre}
            onChange={handleSubgenreChange}
          >
            <option value="">All subgenres</option>
            {SUBGENRES.map((option) => (
              <option key={option.code} value={option.code}>
                {option.name}
              </option>
            ))}
          </select>
        </div>
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
          </>
        )
      ) : null}
    </section>
  )
}
