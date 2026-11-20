import type {
  GraphLayoutMode,
  ProducerGraphView,
  ProducerOverviewSort,
} from '../api/producerGraph'
import type { GraphRole } from '../graph/adapter'
import { FORCE_ENGINES, type ForceEngine } from '../graph/forceLayouts'
import { GraphLimitField } from './GraphLimitField'
import { PeriodFilter } from './PeriodFilter'
import { TaxonomySelect } from './TaxonomySelect'

export type OverviewOptions = {
  view: ProducerGraphView
  producerLimit: number
  bandLimit: number
  albumLimit: number
  producerSort: ProducerOverviewSort
  order: 'asc' | 'desc'
  decade: string
  subgenre: string
  layout: GraphLayoutMode
  engine: ForceEngine
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

const LAYOUTS: Array<{ value: GraphLayoutMode; label: string }> = [
  { value: 'force', label: 'Force' },
  { value: 'bipartite', label: 'Bipartite' },
  { value: 'community', label: 'Community' },
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

      <GraphLimitField
        id="overview-bands"
        label="Band limit"
        value={options.bandLimit}
        fallback={100}
        onChange={(bandLimit) => onOptionsChange({ ...options, bandLimit })}
      />

      <GraphLimitField
        id="overview-albums"
        label="Album limit"
        value={options.albumLimit}
        fallback={500}
        onChange={(albumLimit) => onOptionsChange({ ...options, albumLimit })}
      />

      <div className="field graph-field">
        <label htmlFor="overview-layout">Layout</label>
        <select
          id="overview-layout"
          value={options.layout}
          onChange={(event) =>
            onOptionsChange({
              ...options,
              layout: event.target.value as GraphLayoutMode,
            })
          }
        >
          {LAYOUTS.map((layout) => (
            <option key={layout.value} value={layout.value}>
              {layout.label}
            </option>
          ))}
        </select>
      </div>

      <div className="field graph-field engine-field">
        <span className="field-label" id="overview-engine-label">
          Force engine
        </span>
        <div className="view-tabs" role="group" aria-labelledby="overview-engine-label">
          {FORCE_ENGINES.map((engine) => (
            <button
              key={engine.value}
              type="button"
              className={
                options.engine === engine.value ? 'button' : 'button button--secondary'
              }
              aria-pressed={options.engine === engine.value}
              disabled={options.layout !== 'force'}
              onClick={() => onOptionsChange({ ...options, engine: engine.value })}
            >
              {engine.label}
            </button>
          ))}
        </div>
        {options.layout !== 'force' ? (
          <span className="graph-field-note">Available when Layout is Force.</span>
        ) : null}
      </div>

      <GraphLimitField
        id="overview-producers"
        label="Producers"
        value={options.producerLimit}
        fallback={100}
        max={1000}
        commitOnBlur
        onChange={(producerLimit) => onOptionsChange({ ...options, producerLimit })}
      />

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
