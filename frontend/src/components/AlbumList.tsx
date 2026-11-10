import { Link } from 'react-router'

import type { AlbumListItem } from '../api/albums'

export function AlbumList({ items }: { items: AlbumListItem[] }) {
  return (
    <div className="table-wrap" tabIndex={0} aria-label="Album index">
      <table className="data-table">
        <caption className="sr-only">Albums in the active corpus</caption>
        <thead>
          <tr>
            <th scope="col">Album</th>
            <th scope="col">Band</th>
            <th scope="col">Year</th>
            <th scope="col">Subgenre</th>
            <th scope="col">Producers</th>
          </tr>
        </thead>
        <tbody>
          {items.map((album) => (
            <tr key={album.id}>
              <th scope="row">
                <Link to={`/albums/${album.id}`}>{album.title}</Link>
              </th>
              <td>
                <Link to={`/bands/${album.band_id}`}>{album.band_name}</Link>
              </td>
              <td>{album.year ?? 'Unknown'}</td>
              <td>{album.primary_subgenre ?? 'Unclassified'}</td>
              <td>{album.producer_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
