import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'

import { ApiError } from '../api/client'
import { getHealth } from '../api/health'
import { ApiStatus, type ApiState } from './ApiStatus'
import { SearchBox } from './SearchBox'

const NAV_ITEMS = [
  { to: '/bands', label: 'Bands' },
  { to: '/albums', label: 'Albums' },
  { to: '/producers', label: 'Producers' },
  { to: '/graph', label: 'Graph' },
]

const RAIL_PREFERENCE_KEY = 'hmde:rail-collapsed'

function readRailPreference(): boolean | null {
  try {
    const value = window.localStorage.getItem(RAIL_PREFERENCE_KEY)
    if (value === 'true') return true
    if (value === 'false') return false
  } catch {
    // Storage can be unavailable in private browsing or tests.
  }
  return null
}

function writeRailPreference(value: boolean): void {
  try {
    window.localStorage.setItem(RAIL_PREFERENCE_KEY, String(value))
  } catch {
    // The visual state still works without persistence.
  }
}

function defaultRailCollapsed(pathname: string): boolean {
  return pathname === '/graph'
}

export function AppShell() {
  const location = useLocation()
  const [apiState, setApiState] = useState<ApiState>({ status: 'loading' })
  const [railPreference, setRailPreference] = useState<boolean | null>(() =>
    readRailPreference(),
  )
  const railCollapsed = railPreference ?? defaultRailCollapsed(location.pathname)

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

  function toggleRail() {
    const next = !railCollapsed
    setRailPreference(next)
    writeRailPreference(next)
  }

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className={`app-shell${railCollapsed ? ' app-shell--rail-collapsed' : ''}`}>
        <aside id="site-index-rail" className="index-rail" aria-label="Site navigation">
          <button
            type="button"
            className="rail-toggle"
            aria-expanded={!railCollapsed}
            aria-controls="site-index-rail-content"
            aria-label={railCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            onClick={toggleRail}
          >
            <span aria-hidden="true">{railCollapsed ? '»' : '«'}</span>
          </button>
          <Link to="/bands" className="rail-brand" aria-label="HMDE home">
            H
          </Link>

          <div id="site-index-rail-content" className="index-rail__content">
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
          </div>
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
