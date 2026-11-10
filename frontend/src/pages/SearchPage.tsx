import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'

import { queryKeys } from '../api/queryKeys'
import { searchEntities } from '../api/search'
import { AsyncState } from '../components/AsyncState'
import { SearchResults } from '../components/SearchResults'

export function SearchPage() {
  const [searchParams] = useSearchParams()
  const q = (searchParams.get('q') ?? '').trim()
  const searchQuery = useQuery({
    queryKey: queryKeys.search(q, 10),
    queryFn: () => searchEntities(q, 10),
    enabled: q.length > 0,
  })

  return (
    <section className="page" aria-labelledby="search-heading">
      <header className="page-header">
        <h1 id="search-heading">Search</h1>
        <p>{q ? `Matches for “${q}” across the archive.` : 'Enter a band, album or producer name in the search field.'}</p>
      </header>

      {!q ? <AsyncState status="empty" message="Type a query to search the archive." /> : null}
      {q && searchQuery.isPending ? <AsyncState status="loading" message="Searching…" /> : null}
      {q && searchQuery.isError ? (
        <AsyncState status="error" message="Could not search the archive." onRetry={() => void searchQuery.refetch()} />
      ) : null}
      {q && searchQuery.isSuccess ? <SearchResults results={searchQuery.data} /> : null}
    </section>
  )
}
