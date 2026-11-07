export type AsyncStateStatus = 'loading' | 'error' | 'empty' | 'not-found'

const defaultMessages: Record<AsyncStateStatus, string> = {
  loading: 'Loading…',
  error: 'Something went wrong while loading data.',
  empty: 'Nothing to show yet.',
  'not-found': 'The requested resource was not found.',
}

type AsyncStateProps = {
  status: AsyncStateStatus
  message?: string
  onRetry?: () => void
}

export function AsyncState({ status, message, onRetry }: AsyncStateProps) {
  const text = message ?? defaultMessages[status]

  if (status === 'loading') {
    return (
      <p className="async-state" role="status" aria-live="polite">
        {text}
      </p>
    )
  }

  if (status === 'error') {
    return (
      <div className="async-state async-state--error" role="alert">
        <p>{text}</p>
        {onRetry ? (
          <button type="button" className="button" onClick={onRetry}>
            Retry
          </button>
        ) : null}
      </div>
    )
  }

  return (
    <p className="async-state" role="status">
      {text}
    </p>
  )
}
