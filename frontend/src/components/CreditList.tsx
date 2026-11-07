import type { CreditResponse } from '../api/bands'

function formatScope(scope: string) {
  switch (scope) {
    case 'release':
      return 'Release'
    case 'release_group':
      return 'Release group'
    case 'recording':
      return 'Recording'
    default:
      return scope
  }
}

function formatStatus(status: string) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function supportText(credit: CreditResponse) {
  if (credit.scope === 'release' || credit.scope === 'release_group') {
    return 'Full album'
  }
  return `${credit.supporting_recording_count} of ${credit.recording_count} recordings`
}

export function CreditList({
  albumTitle,
  credits,
}: {
  albumTitle: string
  credits: CreditResponse[]
}) {
  if (credits.length === 0) {
    return (
      <p className="empty-credits">
        No documented credits for this album. Absence is not evidence of
        non-participation.
      </p>
    )
  }

  return (
    <div className="table-wrap">
      <table className="data-table credit-table">
        <caption className="sr-only">Credits for {albumTitle}</caption>
        <thead>
          <tr>
            <th scope="col">Artist</th>
            <th scope="col">Role</th>
            <th scope="col">Scope</th>
            <th scope="col">Support</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {credits.map((credit) => (
            <tr key={`${credit.artist_id}-${credit.role}-${credit.scope}`}>
              <th scope="row">{credit.artist_name}</th>
              <td>{credit.role_name}</td>
              <td>{formatScope(credit.scope)}</td>
              <td>{supportText(credit)}</td>
              <td>{formatStatus(credit.status)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
