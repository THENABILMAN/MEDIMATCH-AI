import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: string
  actions?: ReactNode
}

/** Every signed-in screen opens on a serial slip, so the product is recognisable at a glance. */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="slip on-navy mb-6 flex flex-col gap-4 bg-navy px-6 py-6 md:flex-row md:items-center md:justify-between md:px-8">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold">{title}</h1>
        {description && <p className="prose-width mt-1 text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  )
}
