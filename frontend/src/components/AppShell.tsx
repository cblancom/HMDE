import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router'

import { ApiError } from '../api/client'
import { getHealth } from '../api/health'
import { ApiStatus, type ApiState } from './ApiStatus'
import { SearchBox } from './SearchBox'

const NAV_ITEMS = [
  { to: '/bands', label: 'Bands' },
  { to: '/albums', label: 'Albums' },
  { to: '/producers', label: 'Producers' },
]

export function AppShell() {
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
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="app-shell">
        <aside className="index-rail">
          <header className="site-header">
            <div>
              <Link to="/bands" className="site-title">
                HMDE
              </Link>
              <p className="site-subtitle">Heavy Metal Data Explorer</p>
            </div>
            <ApiStatus state={apiState} />
          </header>

          <nav className="primary-nav" aria-label="Primary">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.to} to={item.to}>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <SearchBox />

          <p className="index-note">
            Documented production credits. Absence is not evidence of
            non-participation.
          </p>
        </aside>

        <main id="main-content" className="site-main">
          <p className="signal-path" aria-label="Archive structure">
            band <span>credited on</span> album <span>produced by</span> producer
          </p>
          <Outlet />
        </main>
      </div>
    </>
  )
}
