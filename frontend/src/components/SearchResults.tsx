import { Link } from 'react-router'

import type { SearchResponse } from '../api/search'

export function SearchResults({ results }: { results: SearchResponse }) {
  const total = results.bands.length + results.albums.length + results.producers.length

  if (total === 0) {
    return <p className="async-state" role="status">No matches for “{results.query}”. Try a broader name.</p>
  }

  return (
    <div className="search-results">
      {results.bands.length > 0 ? (
        <section aria-labelledby="search-bands-heading" className="result-group">
          <h2 id="search-bands-heading">Bands</h2>
          <ul className="result-list">
            {results.bands.map((band) => (
              <li key={band.id}>
                <Link to={`/bands/${band.id}`}>{band.name}</Link>
                <span>{band.subgenre ?? 'Uncategorized'}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {results.albums.length > 0 ? (
        <section aria-labelledby="search-albums-heading" className="result-group">
          <h2 id="search-albums-heading">Albums</h2>
          <ul className="result-list">
            {results.albums.map((album) => (
              <li key={album.id}>
                <Link to={`/albums/${album.id}`}>{album.title}</Link>
                <span>{album.band_name}, {album.year ?? 'year unknown'}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {results.producers.length > 0 ? (
        <section aria-labelledby="search-producers-heading" className="result-group">
          <h2 id="search-producers-heading">Producers</h2>
          <ul className="result-list">
            {results.producers.map((producer) => (
              <li key={producer.id}>
                <Link to={`/producers/${producer.id}`}>{producer.name}</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}
