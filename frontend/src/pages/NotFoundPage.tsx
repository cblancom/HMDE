import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <section className="page" aria-labelledby="not-found-heading">
      <header className="page-header">
        <h1 id="not-found-heading">Page not found</h1>
        <p>The address does not match a page in the archive.</p>
      </header>
      <p>
        <Link to="/bands">Go to the band index</Link>
      </p>
    </section>
  )
}
