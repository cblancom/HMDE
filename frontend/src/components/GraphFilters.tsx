import type { GraphFilters as GraphFilterState, GraphRole } from '../graph/adapter'

type GraphFiltersProps = {
  filters: GraphFilterState
  decades: string[]
  subgenres: string[]
  supportsDecade: boolean
  supportsSubgenre: boolean
  onChange: (filters: GraphFilterState) => void
}

export function GraphFilters({
  filters,
  decades,
  subgenres,
  supportsDecade,
  supportsSubgenre,
  onChange,
}: GraphFiltersProps) {
  return (
    <div className="graph-filters">
      <div className="field graph-field">
        <label htmlFor="graph-role">Role</label>
        <select
          id="graph-role"
          value={filters.role}
          onChange={(event) => onChange({ ...filters, role: event.target.value as GraphRole })}
        >
          <option value="all">All core roles</option>
          <option value="producer">Producer</option>
          <option value="co-producer">Co-producer</option>
        </select>
      </div>
      <div className="field graph-field">
        <label htmlFor="graph-decade">Decade</label>
        <select
          id="graph-decade"
          value={filters.decade}
          onChange={(event) => onChange({ ...filters, decade: event.target.value })}
          disabled={!supportsDecade}
        >
          <option value="">All decades</option>
          {decades.map((decade) => <option key={decade} value={decade}>{decade}</option>)}
        </select>
      </div>
      <div className="field graph-field">
        <label htmlFor="graph-subgenre">Subgenre</label>
        <select
          id="graph-subgenre"
          value={filters.subgenre}
          onChange={(event) => onChange({ ...filters, subgenre: event.target.value })}
          disabled={!supportsSubgenre}
        >
          <option value="">All subgenres</option>
          {subgenres.map((subgenre) => <option key={subgenre} value={subgenre}>{subgenre}</option>)}
        </select>
      </div>
      <p className="graph-note">
        Filters apply to the loaded network. {supportsDecade ? '' : 'Decade and subgenre filters are available in the Albums view.'}
      </p>
    </div>
  )
}
