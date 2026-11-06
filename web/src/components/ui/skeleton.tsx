import type { ComponentProps } from 'react'
import { cn } from '../../lib/cn'

export function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return <div aria-hidden className={cn('animate-pulse-soft rounded-lg bg-border', className)} {...props} />
}
