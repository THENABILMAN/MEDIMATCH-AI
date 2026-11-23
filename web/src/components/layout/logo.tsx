import { Link } from 'react-router-dom'
import { cn } from '../../lib/cn'

/*
 * The MediMatch mark: two rings, the patient and the doctor, overlap.
 * Where they meet is solid and holds a medical cross, because the match is where care starts.
 * It draws in currentColor, with the cross cut out in the surface colour, so it works on any background.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden focusable="false" className={cn('shrink-0', className)}>
      <circle cx="15" cy="20" r="11" stroke="currentColor" strokeWidth="3" />
      <circle cx="25" cy="20" r="11" stroke="currentColor" strokeWidth="3" />
      <path d="M20 10.2A11 11 0 0 1 20 29.8A11 11 0 0 1 20 10.2Z" fill="currentColor" />
      <path d="M18.75 16.5h2.5v2.25h2.25v2.5h-2.25v2.25h-2.5v-2.25H16.5v-2.5h2.25z" fill="var(--surface)" />
    </svg>
  )
}

export function Logo() {
  return (
    <Link
      to="/"
      className="flex shrink-0 items-center gap-2 rounded-lg title-2 whitespace-nowrap sm:heading-5"
      translate="no"
    >
      <LogoMark className="size-7 sm:size-8" />
      <span>
        Medi<span className="text-muted">Match</span>
      </span>
    </Link>
  )
}

/* The large lockup for the hero: mark, name and a short line about what MediMatch does */
export function LogoLockup({ tagline }: { tagline: string }) {
  return (
    <div className="flex items-center gap-3" translate="no">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-primary text-white sm:size-16">
        <LogoMark className="size-10 [--surface:var(--primary)] sm:size-12" />
      </span>
      <span className="flex flex-col">
        <span className="heading-5">
          Medi<span className="text-muted">Match</span>
        </span>
        <span className="body-6 text-muted">{tagline}</span>
      </span>
    </div>
  )
}
