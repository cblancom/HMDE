export type ApiState =
  | { status: 'loading' }
  | { status: 'available' }
  | { status: 'degraded' }
  | { status: 'unavailable' }

const messages: Record<ApiState['status'], string> = {
  loading: 'Checking API status…',
  available: 'API available.',
  degraded: 'API degraded: database unavailable.',
  unavailable: 'API unavailable. The interface is still available.',
}

export function ApiStatus({ state }: { state: ApiState }) {
  return (
    <p
      className={`api-status api-status--${state.status}`}
      role="status"
      aria-live="polite"
    >
      {messages[state.status]}
    </p>
  )
}
