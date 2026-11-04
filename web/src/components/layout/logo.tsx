import { Link } from 'react-router-dom'
import { cn } from '../../lib/cn'

/** A chamber's serial slip, notched where it tears from the book. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 32 32" className={className}>
      <path
        fill="currentColor"
        fillRule="evenodd"
        d="M5 5h22a2 2 0 0 1 2 2v5.5a3.5 3.5 0 0 0 0 7V25a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-5.5a3.5 3.5 0 0 0 0-7V7a2 2 0 0 1 2-2Zm4.5 16h2.6v-6.2l3 4.1h.8l3-4.1V21h2.6V11h-2.6L16 15.9 12.1 11H9.5v10Z"
      />
    </svg>
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <Link to="/" className={cn('flex shrink-0 items-center gap-2 rounded-sm', className)} translate="no">
      <LogoMark className="size-8" />
      <span className="sr-only text-xl font-semibold tracking-tight whitespace-nowrap min-[440px]:not-sr-only">MediMatch</span>
    </Link>
  )
}
