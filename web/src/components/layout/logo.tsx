import { Link } from 'react-router-dom'

export function Logo() {
  return (
    <Link to="/" className="shrink-0 rounded-lg title-2 sm:heading-5 whitespace-nowrap" translate="no">
      MediMatch
    </Link>
  )
}
