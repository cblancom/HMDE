export type GraphLimitFieldProps = {
  id: string
  label: string
  value: number
  fallback: number
  max?: number
  commitOnBlur?: boolean
  onChange: (value: number) => void
}

export function GraphLimitField({
  id,
  label,
  value,
  fallback,
  max = 5000,
  commitOnBlur = false,
  onChange,
}: GraphLimitFieldProps) {
  const all = value === 0
  const clamp = (next: number) => Math.min(Math.max(next, 1), max)
  const commit = (raw: string) => {
    if (raw.trim() === '') {
      onChange(0)
      return
    }
    const next = Number(raw)
    if (!Number.isInteger(next)) return
    onChange(next === 0 ? 0 : clamp(next))
  }
  return (
    <div className="field graph-field">
      <label htmlFor={id}>{label}</label>
      <div className="limit-field">
        <input
          key={commitOnBlur ? `${id}-${all ? 'all' : value}` : undefined}
          id={id}
          type="number"
          min={1}
          max={max}
          {...(commitOnBlur
            ? { defaultValue: all ? '' : String(value) }
            : { value: all ? '' : value })}
          placeholder="All"
          disabled={all}
          onChange={
            commitOnBlur
              ? undefined
              : (event) => {
                  const next = Number(event.target.value)
                  if (Number.isInteger(next) && next > 0) onChange(clamp(next))
                }
          }
          onBlur={commitOnBlur ? (event) => commit(event.currentTarget.value) : undefined}
          onKeyDown={
            commitOnBlur
              ? (event) => {
                  if (event.key === 'Enter') event.currentTarget.blur()
                  if (event.key === 'Escape') {
                    event.currentTarget.value = all ? '' : String(value)
                    event.currentTarget.blur()
                  }
                }
              : undefined
          }
        />
        <label className="limit-field__all">
          <input
            type="checkbox"
            checked={all}
            aria-label={`${label} all`}
            onChange={(event) => onChange(event.target.checked ? 0 : fallback)}
          />
          All
        </label>
      </div>
    </div>
  )
}
