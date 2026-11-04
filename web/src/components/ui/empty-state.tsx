import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface EmptyStateProps {
  title: string
  description: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('rounded-md border border-border bg-surface p-6 md:p-8', className)}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="prose-width mt-1 text-muted">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
