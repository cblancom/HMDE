import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'

import { ApiError } from '../api/client'
import { getAlbum } from '../api/albums'
import { queryKeys } from '../api/queryKeys'
import { AsyncState } from '../components/AsyncState'
import { CreditList } from '../components/CreditList'

export function AlbumDetailPage() {
  const { albumId } = useParams()
  const id = albumId ?? ''
  const albumQuery = useQuery({
    queryKey: queryKeys.album(id),
    queryFn: () => getAlbum(id),
    enabled: id.length > 0,
  })

  if (!id) {
    return <AsyncState status="not-found" message="Album not found." />
  }
  if (albumQuery.isPending) {
    return <AsyncState status="loading" message="Loading album…" />
  }
  if (albumQuery.isError) {
    const notFound = albumQuery.error instanceof ApiError && albumQuery.error.status === 404
    return notFound ? (
      <AsyncState status="not-found" message="Album not found." />
    ) : (
      <AsyncState status="error" message="Could not load this album." onRetry={() => void albumQuery.refetch()} />
    )
  }

  const album = albumQuery.data
  return (
    <section className="page" aria-labelledby="album-heading">
      <p><Link to="/albums">← Back to albums</Link></p>
      <header className="detail-header">
        <h1 id="album-heading">{album.title}</h1>
        <dl className="metadata">
          <div><dt>Band</dt><dd><Link to={`/bands/${album.band_id}`}>{album.band_name}</Link></dd></div>
          <div><dt>Year</dt><dd>{album.year ?? 'Unknown'}</dd></div>
          <div><dt>Subgenre</dt><dd>{album.primary_subgenre ?? 'Unclassified'}</dd></div>
          <div><dt>MusicBrainz ID</dt><dd className="mono">{album.mbid}</dd></div>
        </dl>
        {album.secondary_subgenres.length > 0 ? (
          <p>Also classified as {album.secondary_subgenres.join(', ')}.</p>
        ) : null}
      </header>
      <section aria-labelledby="album-credits-heading">
        <h2 id="album-credits-heading">Credits</h2>
        <CreditList albumTitle={album.title} credits={album.credits} />
      </section>
    </section>
  )
}
