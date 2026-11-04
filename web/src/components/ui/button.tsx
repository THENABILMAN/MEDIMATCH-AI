import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import type { ComponentProps } from 'react'
import { Slot } from 'radix-ui'
import { cn } from '../../lib/cn'

export const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-sm font-medium whitespace-nowrap transition-colors select-none disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'bg-primary text-on-primary hover:bg-primary-hover active:bg-primary-pressed',
        secondary:
          'border border-control bg-transparent text-ink hover:bg-primary-tint active:bg-border',
        ghost: 'text-ink hover:bg-primary-tint active:bg-border',
        danger: 'bg-danger text-white hover:bg-danger-pressed active:bg-danger-pressed',
        link: 'text-primary underline underline-offset-4 hover:text-primary-hover active:text-primary-pressed',
      },
      size: {
        md: 'h-11 px-4 text-md md:h-10 md:text-sm',
        sm: 'h-11 px-3 text-sm md:h-8',
        lg: 'h-13 px-6 text-md font-semibold',
        inline: 'h-auto p-0 text-[length:inherit]',
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
  const classes = cn(buttonVariants({ variant, size }), className)

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
      {loading && <Loader2 aria-hidden className="size-4 animate-spin" strokeWidth={1.75} />}
      {children}
    </button>
  )
}
