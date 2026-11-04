import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '../../lib/cn'
import { Tooltip } from './tooltip'

const iconButtonVariants = cva(
  'inline-flex size-11 shrink-0 items-center justify-center rounded-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 md:size-10',
  {
    variants: {
      variant: {
        ghost: 'text-ink hover:bg-canvas active:bg-border',
        outline: 'border border-control bg-surface text-ink hover:bg-canvas active:bg-border',
        danger: 'text-danger hover:bg-danger-tint active:bg-danger-tint',
      },
    },
    defaultVariants: { variant: 'ghost' },
  }
)

interface IconButtonProps
  extends Omit<ComponentProps<'button'>, 'aria-label'>,
    VariantProps<typeof iconButtonVariants> {
  label: string
}

export function IconButton({ label, variant, className, type, ...props }: IconButtonProps) {
  return (
    <Tooltip content={label}>
      <button
        type={type ?? 'button'}
        aria-label={label}
        className={cn(iconButtonVariants({ variant }), className)}
        {...props}
      />
    </Tooltip>
  )
}
