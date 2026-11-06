import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { Illustration, type IllustrationName } from './illustration'

interface EmptyStateProps {
  title: string
  description: string
  action?: ReactNode
  illustration?: IllustrationName
  className?: string
}

export function EmptyState({ title, description, action, illustration, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col gap-4 rounded-xl bg-surface p-6 sm:flex-row sm:items-start md:p-8', className)}>
      {illustration && <Illustration name={illustration} />}
      <div className="min-w-0">
        <h2 className="heading-5">{title}</h2>
        <p className="prose-width mt-1 text-muted">{description}</p>
        {action && <div className="mt-4">{action}</div>}
      </div>
    </div>
  )
}
