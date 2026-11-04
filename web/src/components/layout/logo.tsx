import { Link } from 'react-router-dom'

/** Two overlapping rings: the patient and the doctor who suits them. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 32 32" fill="none" className={className}>
      <circle cx="12" cy="16" r="9" stroke="var(--primary)" strokeWidth="3" />
      <circle cx="20" cy="16" r="9" stroke="var(--primary)" strokeWidth="3" />
    </svg>
  )
}

export function Logo() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2 rounded-sm" translate="no">
      <LogoMark className="size-7" />
      <span className="font-serif text-lg font-medium whitespace-nowrap">MediMatch</span>
    </Link>
  )
}
