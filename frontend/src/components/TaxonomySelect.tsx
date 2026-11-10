import { useQuery } from '@tanstack/react-query'

import { getTaxonomy } from '../api/taxonomy'
import { queryKeys } from '../api/queryKeys'

type TaxonomySelectProps = {
  value: string
  onChange: (value: string) => void
}

export function TaxonomySelect({ value, onChange }: TaxonomySelectProps) {
  const taxonomyQuery = useQuery({
    queryKey: queryKeys.taxonomy,
    queryFn: getTaxonomy,
    staleTime: 5 * 60_000,
  })

  return (
    <div className="field">
      <label htmlFor="taxonomy-filter">Subgenre</label>
      <select
        id="taxonomy-filter"
        name="subgenre"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={taxonomyQuery.isPending}
      >
        <option value="">
          {taxonomyQuery.isError ? 'Taxonomy unavailable' : 'All subgenres'}
        </option>
        {taxonomyQuery.data?.nodes.map((node) => (
          <option key={node.code} value={node.code}>
            {node.parent_code ? `— ${node.name}` : node.name}
          </option>
        ))}
      </select>
    </div>
  )
}
