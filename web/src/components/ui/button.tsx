import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { Slot } from 'radix-ui'
import { cn } from '../../lib/cn'

export const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-full whitespace-nowrap transition-[color,background-color,border-color,opacity,transform] select-none active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 aria-disabled:cursor-not-allowed aria-disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-white hover:bg-primary-hover active:bg-primary-pressed',
        secondary: 'border border-control bg-surface text-ink hover:bg-canvas active:bg-border',
        ghost: 'text-ink hover:bg-canvas active:bg-border',
        danger: 'bg-danger text-white hover:bg-danger-pressed active:bg-danger-pressed',
        link: 'text-primary underline underline-offset-4 hover:text-primary-hover active:text-primary-pressed',
      },
      size: {
        md: 'button-md min-h-11 px-3 py-2 md:min-h-10',
        sm: 'button-sm min-h-11 px-3 py-1 md:min-h-8',
        lg: 'button-md min-h-12 px-3 py-2',
        inline: 'h-auto p-0 [font:inherit]',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
)

export interface ButtonProps extends ComponentProps<'button'>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

export function Button({
  variant,
  size,
  asChild = false,
  loading = false,
  disabled,
  className,
  children,
  type,
  ...props
}: ButtonProps) {
  const classes = cn(buttonVariants({ variant, size }), loading && 'animate-pulse-soft', className)

  if (asChild) {
    return (
      <Slot.Root className={classes} {...props}>
        {children}
      </Slot.Root>
    )
  }

  return (
    <button
      type={type ?? 'button'}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {children}
    </button>
  )
}
