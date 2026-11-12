import { Link } from 'react-router'

import type { OverviewIndexRow } from '../graph/adapter'

type OverviewIndexProps = {
  producers: OverviewIndexRow[]
  bands: OverviewIndexRow[]
  bandsLoading?: boolean
  bandsError?: boolean
  onRetryBands?: () => void
}

export function OverviewIndex({
  producers,
  bands,
  bandsLoading = false,
  bandsError = false,
  onRetryBands,
}: OverviewIndexProps) {
  return (
    <aside className="overview-index" aria-label="Network index">
      <p className="overview-index__note">Album counts in the loaded network.</p>

      <details className="overview-index__section">
        <summary>
          <span>Producers</span>
          <span className="overview-index__count">{producers.length}</span>
        </summary>
        {producers.length === 0 ? (
          <p className="overview-index__empty">No producers in the loaded network.</p>
        ) : (
          <ol className="overview-index__list">
            {producers.map((row) => (
              <li key={row.id}>
                <Link to={`/producers/${row.id}`}>{row.label}</Link>
                <span className="overview-index__count">{row.count}</span>
              </li>
            ))}
          </ol>
        )}
      </details>

      <details className="overview-index__section">
        <summary>
          <span>Bands</span>
          <span className="overview-index__count">{bands.length}</span>
        </summary>
        {bandsLoading ? (
          <p className="overview-index__empty">Loading bands…</p>
        ) : bandsError ? (
          <div className="overview-index__error">
            <p>Band index unavailable.</p>
            {onRetryBands ? (
              <button type="button" className="button button--secondary" onClick={onRetryBands}>
                Retry
              </button>
            ) : null}
          </div>
        ) : bands.length === 0 ? (
          <p className="overview-index__empty">No bands in the loaded network.</p>
        ) : (
          <ol className="overview-index__list">
            {bands.map((row) => (
              <li key={row.id}>
                <Link to={`/bands/${row.id}`}>{row.label}</Link>
                <span className="overview-index__count">{row.count}</span>
              </li>
            ))}
          </ol>
        )}
      </details>
    </aside>
  )
}
