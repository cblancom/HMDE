import { Link } from 'react-router'

import type { BandListItem } from '../api/bands'

export function BandList({ items }: { items: BandListItem[] }) {
  return (
    <div className="table-wrap" tabIndex={0} aria-label="Band index">
      <table className="data-table">
        <caption className="sr-only">Bands in the active corpus</caption>
        <thead>
          <tr>
            <th scope="col">Band</th>
            <th scope="col">Country</th>
            <th scope="col">Subgenre</th>
            <th scope="col">Albums</th>
          </tr>
        </thead>
        <tbody>
          {items.map((band) => (
            <tr key={band.id}>
              <th scope="row">
                <Link to={`/bands/${band.id}`}>{band.name}</Link>
              </th>
              <td>{band.country ?? 'Unknown'}</td>
              <td>{band.subgenre ?? 'Uncategorized'}</td>
              <td>{band.album_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
