import { useSearchParams } from 'react-router'

type PaginationProps = {
  total: number
  limit: number
  offset: number
}

export function Pagination({ total, limit, offset }: PaginationProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const hasPrevious = offset > 0
  const hasNext = offset + limit < total

  function move(nextOffset: number) {
    const params = new URLSearchParams(searchParams)
    if (nextOffset > 0) {
      params.set('offset', String(nextOffset))
    } else {
      params.delete('offset')
    }
    setSearchParams(params)
  }

  const page = Math.floor(offset / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))

  return (
    <nav className="pagination" aria-label="Result pages">
      <button
        type="button"
        className="button button--secondary"
        onClick={() => move(Math.max(0, offset - limit))}
        disabled={!hasPrevious}
      >
        Previous
      </button>
      <p className="pagination__status">
        Page {page} of {pages}
      </p>
      <button
        type="button"
        className="button button--secondary"
        onClick={() => move(offset + limit)}
        disabled={!hasNext}
      >
        Next
      </button>
    </nav>
  )
}
