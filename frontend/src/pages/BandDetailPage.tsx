import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { ApiError } from '../api/client'
import { getBand, getBandGraph } from '../api/bands'
import { AsyncState } from '../components/AsyncState'
import { BandGraph } from '../components/BandGraph'
import { CreditList } from '../components/CreditList'

export function BandDetailPage() {
  const { bandId } = useParams()
  const id = bandId ?? ''

  const bandQuery = useQuery({
    queryKey: ['band', id],
    queryFn: () => getBand(id),
    enabled: id.length > 0,
  })

  const graphQuery = useQuery({
    queryKey: ['band-graph', id],
    queryFn: () => getBandGraph(id),
    enabled: id.length > 0 && bandQuery.isSuccess,
  })

  if (!id) {
    return (
      <section className="page">
        <p>
          <Link to="/bands">← Back to bands</Link>
        </p>
        <AsyncState status="not-found" message="Band not found." />
      </section>
    )
  }

  if (bandQuery.isPending) {
    return (
      <section className="page">
        <p>
          <Link to="/bands">← Back to bands</Link>
        </p>
        <AsyncState status="loading" message="Loading band…" />
      </section>
    )
  }

  if (bandQuery.isError) {
    const notFound = bandQuery.error instanceof ApiError && bandQuery.error.status === 404

    return (
      <section className="page">
        <p>
          <Link to="/bands">← Back to bands</Link>
        </p>
        {notFound ? (
          <AsyncState status="not-found" message="Band not found." />
        ) : (
          <AsyncState
            status="error"
            message="Could not load this band."
            onRetry={() => void bandQuery.refetch()}
          />
        )}
      </section>
    )
  }

  const band = bandQuery.data

  return (
    <section className="page" aria-labelledby="band-heading">
      <p>
        <Link to="/bands">← Back to bands</Link>
      </p>

      <header className="detail-header">
        <p className="eyebrow">{band.subgenre ?? 'Uncategorized'}</p>
        <h1 id="band-heading">{band.name}</h1>
        <dl className="metadata">
          <div>
            <dt>Country</dt>
            <dd>{band.country ?? 'Unknown'}</dd>
          </div>
          <div>
            <dt>MusicBrainz ID</dt>
            <dd className="mono">{band.mbid}</dd>
          </div>
          <div>
            <dt>Albums</dt>
            <dd>{band.albums.length}</dd>
          </div>
        </dl>
      </header>

      <section aria-labelledby="albums-heading">
        <h2 id="albums-heading">Albums</h2>
        {band.albums.length === 0 ? (
          <AsyncState status="empty" message="No documented albums for this band." />
        ) : (
          <ol className="album-list">
            {band.albums.map((album) => (
              <li key={album.id}>
                <article className="album-card" aria-labelledby={`album-${album.id}`}>
                  <header className="album-header">
                    <h3 id={`album-${album.id}`}>
                      <Link to={`/albums/${album.id}`}>{album.title}</Link>
                    </h3>
                    <p>
                      Released {album.year ?? 'year unknown'} <span className="mono">{album.mbid}</span>
                    </p>
                  </header>
                  <CreditList albumTitle={album.title} credits={album.credits} />
                </article>
              </li>
            ))}
          </ol>
        )}
      </section>

      {graphQuery.isPending ? (
        <section className="graph-section" aria-labelledby="graph-heading">
          <h2 id="graph-heading">Producer graph</h2>
          <AsyncState status="loading" message="Loading producer graph…" />
        </section>
      ) : null}

      {graphQuery.isError ? (
        <section className="graph-section" aria-labelledby="graph-heading">
          <h2 id="graph-heading">Producer graph</h2>
          <AsyncState
            status="error"
            message="Could not load the producer graph."
            onRetry={() => void graphQuery.refetch()}
          />
        </section>
      ) : null}

      {graphQuery.isSuccess ? <BandGraph graph={graphQuery.data} /> : null}
    </section>
  )
}
