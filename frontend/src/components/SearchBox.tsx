import type { FormEvent } from 'react'
import { useNavigate } from 'react-router'

export function SearchBox() {
  const navigate = useNavigate()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const field = event.currentTarget.elements.namedItem('q')
    const query = field instanceof HTMLInputElement ? field.value.trim() : ''
    navigate(query ? `/search?q=${encodeURIComponent(query)}` : '/search')
  }

  return (
    <form className="search-box" role="search" onSubmit={handleSubmit}>
      <label htmlFor="global-search">Search the archive</label>
      <div className="search-box__row">
        <input
          id="global-search"
          name="q"
          type="search"
          placeholder="Band, album or producer"
        />
        <button type="submit" className="button">
          Search
        </button>
      </div>
    </form>
  )
}
