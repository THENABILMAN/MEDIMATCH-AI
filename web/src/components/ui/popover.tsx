import { Popover as PopoverPrimitive } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'

interface PopoverProps extends ComponentProps<typeof PopoverPrimitive.Root> {
  trigger: ReactNode
  children: ReactNode
  align?: 'start' | 'center' | 'end'
}

export function Popover({ trigger, children, align = 'end', ...rootProps }: PopoverProps) {
  return (
    <PopoverPrimitive.Root {...rootProps}>
      <PopoverPrimitive.Trigger asChild>{trigger}</PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align={align}
          sideOffset={4}
          className="z-50 w-64 max-w-[calc(100vw-32px)] rounded-md border border-border bg-surface p-3 shadow-overlay"
        >
          {children}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}
