import { cva, type VariantProps } from 'class-variance-authority'
import { Info, Siren, Warning } from '@phosphor-icons/react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

const bannerVariants = cva('flex items-start gap-3 rounded-xl p-4 body-3', {
  variants: {
    tone: {
      info: 'border border-border bg-surface text-ink',
      warning: 'bg-warning-tint text-ink',
      emergency: 'bg-danger text-white',
    },
  },
  defaultVariants: { tone: 'info' },
})

const ICONS = { info: Info, warning: Warning, emergency: Siren }

interface BannerProps extends VariantProps<typeof bannerVariants> {
  title?: string
  children?: ReactNode
  action?: ReactNode
  className?: string
}

export function Banner({ tone = 'info', title, children, action, className }: BannerProps) {
  const Icon = ICONS[tone ?? 'info']
  return (
    <div role={tone === 'info' ? 'status' : 'alert'} className={cn(bannerVariants({ tone }), className)}>
      <Icon
        aria-hidden
        className={cn('mt-0.5 size-5 shrink-0', tone === 'warning' && 'text-warning')}
      />
      <div className="min-w-0 flex-1">
        {title && <p className="body-1">{title}</p>}
        {children}
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  )
}
