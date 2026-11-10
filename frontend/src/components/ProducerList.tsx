import { Link } from 'react-router'

import type { ProducerListItem } from '../api/producers'

function formatMetric(value: number | null, digits = 0) {
  return value === null ? '—' : value.toFixed(digits)
}

export function ProducerList({ items }: { items: ProducerListItem[] }) {
  return (
    <div className="table-wrap" tabIndex={0} aria-label="Producer index">
      <table className="data-table">
        <caption className="sr-only">Producers in the selected analysis run</caption>
        <thead>
          <tr>
            <th scope="col">Producer</th>
            <th scope="col">Albums</th>
            <th scope="col">Bands</th>
            <th scope="col">Self-produced</th>
            <th scope="col">Betweenness</th>
          </tr>
        </thead>
        <tbody>
          {items.map((producer) => (
            <tr key={producer.id}>
              <th scope="row">
                <Link to={`/producers/${producer.id}`}>{producer.name}</Link>
              </th>
              <td>{producer.album_count}</td>
              <td>{producer.band_count}</td>
              <td>{producer.self_produced_albums}</td>
              <td>{formatMetric(producer.betweenness, 3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
