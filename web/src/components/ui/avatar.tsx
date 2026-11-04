import { cn } from '../../lib/cn'

const HONORIFIC = /^(dr|prof|mr|mrs|ms)\.?\s+/i

function initials(name: string): string {
  const parts = name.replace(HONORIFIC, '').trim().split(/\s+/)
  return parts
    .slice(0, 2)
    .map((part) => Array.from(part)[0] ?? '')
    .join('')
    .toUpperCase()
}

interface AvatarProps {
  name: string
  className?: string
}

export function Avatar({ name, className }: AvatarProps) {
  return (
    <span
      aria-hidden
      className={cn(
        'inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-border bg-canvas text-sm font-medium text-muted',
        className
      )}
    >
      {initials(name)}
    </span>
  )
}
