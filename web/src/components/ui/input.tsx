import type { ComponentProps } from 'react'
import { cn } from '../../lib/cn'

export const controlClasses =
  'w-full rounded-lg border border-control bg-surface body-3 text-ink transition-colors placeholder:text-muted hover:border-ink disabled:cursor-not-allowed disabled:bg-canvas disabled:opacity-70 aria-invalid:border-danger'

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return <input className={cn(controlClasses, 'h-11 px-3 md:h-10', className)} {...props} />
}

export function Textarea({ className, ...props }: ComponentProps<'textarea'>) {
  return <textarea className={cn(controlClasses, 'min-h-24 resize-y px-3 py-2', className)} {...props} />
}
