import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { ApiError } from '../api/client'
import { getProducer } from '../api/producers'
import { queryKeys } from '../api/queryKeys'
import { AsyncState } from '../components/AsyncState'

export function ProducerDetailPage() {
  const { producerId } = useParams()
  const id = producerId ?? ''
  const producerQuery = useQuery({
    queryKey: queryKeys.producer(id),
    queryFn: () => getProducer(id),
    enabled: id.length > 0,
  })

  if (!id) return <AsyncState status="not-found" message="Producer not found." />
  if (producerQuery.isPending) return <AsyncState status="loading" message="Loading producer…" />
  if (producerQuery.isError) {
    const notFound = producerQuery.error instanceof ApiError && producerQuery.error.status === 404
    return notFound ? (
      <AsyncState status="not-found" message="Producer not found." />
    ) : (
      <AsyncState status="error" message="Could not load this producer." onRetry={() => void producerQuery.refetch()} />
    )
  }

  const producer = producerQuery.data
  return (
    <section className="page" aria-labelledby="producer-heading">
      <p><Link to="/producers">← Back to producers</Link></p>
      <header className="detail-header">
        <h1 id="producer-heading">{producer.name}</h1>
        <p><Link className="button" to={`/producers/${producer.id}/graph`}>Open graph</Link></p>
        <dl className="metadata">
          <div><dt>Albums</dt><dd>{producer.album_count}</dd></div>
          <div><dt>Bands</dt><dd>{producer.band_count}</dd></div>
          <div><dt>Self-produced albums</dt><dd>{producer.self_produced_albums}</dd></div>
          <div><dt>Betweenness</dt><dd>{producer.betweenness === null ? 'Not available' : producer.betweenness.toFixed(3)}</dd></div>
          <div><dt>Community</dt><dd>{producer.community_key ?? 'Unassigned'}</dd></div>
          <div><dt>Analysis run</dt><dd className="mono">{producer.meta.analysis_version}</dd></div>
        </dl>
      </header>

      <section aria-labelledby="producer-albums-heading">
        <h2 id="producer-albums-heading">Albums</h2>
        {producer.top_albums.length === 0 ? (
          <AsyncState status="empty" message="No documented albums for this producer." />
        ) : (
          <div className="table-wrap" tabIndex={0} aria-label="Producer albums">
            <table className="data-table">
              <caption className="sr-only">Albums by {producer.name}</caption>
              <thead><tr><th scope="col">Album</th><th scope="col">Band</th><th scope="col">Year</th><th scope="col">Role</th></tr></thead>
              <tbody>
                {producer.top_albums.map((album) => (
                  <tr key={album.album_id}>
                    <th scope="row"><Link to={`/albums/${album.album_id}`}>{album.title}</Link></th>
                    <td>{album.band_name}</td>
                    <td>{album.year ?? 'Unknown'}</td>
                    <td>{album.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="producer-bands-heading">
        <h2 id="producer-bands-heading">Bands</h2>
        {producer.top_bands.length === 0 ? (
          <AsyncState status="empty" message="No documented bands for this producer." />
        ) : (
          <div className="table-wrap" tabIndex={0} aria-label="Producer bands">
            <table className="data-table">
              <caption className="sr-only">Bands by {producer.name}</caption>
              <thead><tr><th scope="col">Band</th><th scope="col">Albums</th><th scope="col">Years</th></tr></thead>
              <tbody>
                {producer.top_bands.map((band) => (
                  <tr key={band.band_id}>
                    <th scope="row"><Link to={`/bands/${band.band_id}`}>{band.name}</Link></th>
                    <td>{band.album_count}</td>
                    <td>{band.first_year ?? 'Unknown'}–{band.last_year ?? 'Unknown'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  )
}
