import type { ProducerGraphView, ProducerOverviewSort } from '../api/producerGraph'
import type { GraphRole } from '../graph/adapter'
import { PeriodFilter } from './PeriodFilter'
import { TaxonomySelect } from './TaxonomySelect'

export type OverviewOptions = {
  view: ProducerGraphView
  producerLimit: number
  producerSort: ProducerOverviewSort
  order: 'asc' | 'desc'
  decade: string
  subgenre: string
}

export type OverviewDisplayOptions = {
  role: GraphRole
  hideIsolated: boolean
  producerSearch: string
}

type ProducerOverviewControlsProps = {
  options: OverviewOptions
  display: OverviewDisplayOptions
  onOptionsChange: (options: OverviewOptions) => void
  onDisplayChange: (display: OverviewDisplayOptions) => void
  onReset: () => void
}

const PRODUCER_LIMITS = [
  { value: 0, label: 'All producers' },
  { value: 10, label: 'Top 10' },
  { value: 25, label: 'Top 25' },
  { value: 50, label: 'Top 50' },
  { value: 100, label: 'Top 100' },
]

export function ProducerOverviewControls({
  options,
  display,
  onOptionsChange,
  onDisplayChange,
  onReset,
}: ProducerOverviewControlsProps) {
  return (
    <div className="graph-controls overview-controls">
      <div className="view-tabs" role="group" aria-label="Graph view">
        <button
          type="button"
          className={options.view === 'bands' ? 'button' : 'button button--secondary'}
          aria-pressed={options.view === 'bands'}
          onClick={() => onOptionsChange({ ...options, view: 'bands' })}
        >
          Bands
        </button>
        <button
          type="button"
          className={options.view === 'albums' ? 'button' : 'button button--secondary'}
          aria-pressed={options.view === 'albums'}
          onClick={() => onOptionsChange({ ...options, view: 'albums' })}
        >
          Albums
        </button>
      </div>

      <div className="field graph-field">
        <label htmlFor="overview-producers">Producers</label>
        <select
          id="overview-producers"
          value={options.producerLimit}
          onChange={(event) =>
            onOptionsChange({ ...options, producerLimit: Number(event.target.value) })
          }
        >
          {PRODUCER_LIMITS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="field graph-field">
        <label htmlFor="overview-sort">Sort producers</label>
        <select
          id="overview-sort"
          value={options.producerSort}
          onChange={(event) =>
            onOptionsChange({
              ...options,
              producerSort: event.target.value as ProducerOverviewSort,
            })
          }
        >
          <option value="album_count">Albums</option>
          <option value="band_count">Bands</option>
          <option value="betweenness">Betweenness</option>
          <option value="name">Name</option>
        </select>
      </div>

      <div className="field graph-field">
        <label htmlFor="overview-order">Order</label>
        <select
          id="overview-order"
          value={options.order}
          onChange={(event) =>
            onOptionsChange({ ...options, order: event.target.value as 'asc' | 'desc' })
          }
        >
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>

      <PeriodFilter
        value={options.decade}
        onChange={(decade) => onOptionsChange({ ...options, decade })}
      />
      <TaxonomySelect
        value={options.subgenre}
        onChange={(subgenre) => onOptionsChange({ ...options, subgenre })}
      />

      <div className="field graph-field">
        <label htmlFor="overview-role">Role</label>
        <select
          id="overview-role"
          value={display.role}
          onChange={(event) =>
            onDisplayChange({ ...display, role: event.target.value as GraphRole })
          }
        >
          <option value="all">All core roles</option>
          <option value="producer">Producer</option>
          <option value="co-producer">Co-producer</option>
        </select>
      </div>

      <div className="field graph-field">
        <label htmlFor="overview-producer-search">Highlight producer</label>
        <input
          id="overview-producer-search"
          type="search"
          value={display.producerSearch}
          placeholder="Martin Birch"
          onChange={(event) =>
            onDisplayChange({ ...display, producerSearch: event.target.value })
          }
        />
      </div>

      <label className="overview-toggle">
        <input
          type="checkbox"
          checked={!display.hideIsolated}
          onChange={(event) =>
            onDisplayChange({ ...display, hideIsolated: !event.target.checked })
          }
        />
        Show isolated producers
      </label>

      <button type="button" className="button button--secondary" onClick={onReset}>
        Reset filters
      </button>
    </div>
  )
}
