import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router'

import { ApiError } from './api/client'
import { getHealth } from './api/health'
import { ApiStatus, type ApiState } from './components/ApiStatus'
import { BandDetailPage } from './pages/BandDetailPage'
import { BandsPage } from './pages/BandsPage'

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
    <div className="app-shell">
      <header className="site-header">
        <div>
          <Link to="/bands" className="site-title">
            Heavy Metal Data Explorer
          </Link>
          <p className="site-subtitle">
            Documented production relationships in heavy metal.
          </p>
        </div>
        <ApiStatus state={apiState} />
      </header>
      <main className="site-main">
        <Routes>
          <Route path="/" element={<Navigate to="/bands" replace />} />
          <Route path="/bands" element={<BandsPage />} />
          <Route path="/bands/:bandId" element={<BandDetailPage />} />
          <Route
            path="*"
            element={
              <section className="page">
                <h1>Page not found</h1>
                <p>
                  <Link to="/bands">Return to the band list</Link>
                </p>
              </section>
            }
          />
        </Routes>
      </main>
    </div>
  )
}

export default App
