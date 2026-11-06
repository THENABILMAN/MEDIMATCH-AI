import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '../../lib/cn'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-lg px-2 py-0.5 caption-4 whitespace-nowrap',
  {
    variants: {
      tone: {
        neutral: 'bg-canvas text-muted',
        primary: 'bg-primary-tint text-primary-hover',
        ai: 'bg-ai-tint text-ai',
        success: 'bg-success-tint text-success',
        warning: 'bg-warning-tint text-warning',
        danger: 'bg-danger-tint text-danger',
      },
    },
    defaultVariants: { tone: 'neutral' },
  }
)

export interface BadgeProps extends ComponentProps<'span'>, VariantProps<typeof badgeVariants> {}

export function Badge({ tone, className, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
