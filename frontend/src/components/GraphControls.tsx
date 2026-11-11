import type { ProducerGraphView } from '../api/producerGraph'

type GraphControlsProps = {
  view: ProducerGraphView
  limit: number
  depth: number
  onViewChange: (view: ProducerGraphView) => void
  onLimitChange: (limit: number) => void
  onDepthChange: (depth: number) => void
}

export function GraphControls({
  view,
  limit,
  depth,
  onViewChange,
  onLimitChange,
  onDepthChange,
}: GraphControlsProps) {
  return (
    <div className="graph-controls">
      <div className="view-tabs" role="group" aria-label="Graph view">
        <button
          type="button"
          className={view === 'bands' ? 'button' : 'button button--secondary'}
          aria-pressed={view === 'bands'}
          onClick={() => onViewChange('bands')}
        >
          Bands
        </button>
        <button
          type="button"
          className={view === 'albums' ? 'button' : 'button button--secondary'}
          aria-pressed={view === 'albums'}
          onClick={() => onViewChange('albums')}
        >
          Albums
        </button>
      </div>

      <div className="field graph-field">
        <label htmlFor="graph-limit">Neighbors</label>
        <select
          id="graph-limit"
          value={limit}
          onChange={(event) => onLimitChange(Number(event.target.value))}
        >
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>

      <div className="field graph-field">
        <label htmlFor="graph-depth">Depth</label>
        <select
          id="graph-depth"
          value={depth}
          onChange={(event) => onDepthChange(Number(event.target.value))}
        >
          <option value={1}>1</option>
          <option value={2}>2</option>
        </select>
      </div>
    </div>
  )
}
