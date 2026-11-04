import type { ComponentProps } from 'react'
import { cn } from '../../lib/cn'

export function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return <div aria-hidden className={cn('animate-pulse-soft rounded-sm bg-border', className)} {...props} />
}
