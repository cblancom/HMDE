import { useEffect, useState } from 'react'

import { ApiError } from './api/client'
import { getHealth } from './api/health'
import { ApiStatus, type ApiState } from './components/ApiStatus'

function App() {
  const [apiState, setApiState] = useState<ApiState>({ status: 'loading' })

  useEffect(() => {
    let active = true

    getHealth()
      .then(() => {
        if (active) {
          setApiState({ status: 'available' })
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return
        }

        if (error instanceof ApiError && error.status === 503) {
          setApiState({ status: 'degraded' })
          return
        }

        setApiState({ status: 'unavailable' })
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <main className="app-shell">
      <h1>Heavy Metal Data Explorer</h1>
      <p>Foundations are under construction.</p>
      <ApiStatus state={apiState} />
    </main>
  )
}

export default App
