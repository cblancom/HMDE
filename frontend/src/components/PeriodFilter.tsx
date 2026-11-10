const DECADES = ['1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']

type PeriodFilterProps = {
  value: string
  onChange: (value: string) => void
}

export function PeriodFilter({ value, onChange }: PeriodFilterProps) {
  return (
    <div className="field">
      <label htmlFor="decade-filter">Decade</label>
      <select
        id="decade-filter"
        name="decade"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">All decades</option>
        {DECADES.map((decade) => (
          <option key={decade} value={decade}>
            {decade}
          </option>
        ))}
      </select>
    </div>
  )
}
