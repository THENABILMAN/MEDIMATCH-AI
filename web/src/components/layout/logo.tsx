import { Link } from 'react-router-dom'

export function Logo() {
  return (
    <Link to="/" className="shrink-0 rounded-sm font-serif text-lg font-semibold sm:text-xl whitespace-nowrap" translate="no">
      MediMatch
    </Link>
  )
}
