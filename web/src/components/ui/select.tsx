import { CaretDown, Check } from '@phosphor-icons/react'
import { Select as SelectPrimitive } from 'radix-ui'
import { cn } from '../../lib/cn'
import { controlClasses } from './input'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  id?: string
  value: string
  onValueChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  className?: string
  name?: string
  'aria-label'?: string
  'aria-describedby'?: string
  'aria-invalid'?: true
}

export function Select({
  value,
  onValueChange,
  options,
  placeholder,
  disabled,
  name,
  className,
  ...triggerProps
}: SelectProps) {
  return (
    <SelectPrimitive.Root value={value} onValueChange={onValueChange} disabled={disabled} name={name}>
      <SelectPrimitive.Trigger
        className={cn(
          controlClasses,
          'flex h-11 items-center justify-between gap-2 px-3 text-left data-placeholder:text-muted md:h-10',
          className
        )}
        {...triggerProps}
      >
        <span className="min-w-0 truncate">
          <SelectPrimitive.Value placeholder={placeholder} />
        </span>
        <SelectPrimitive.Icon>
          <CaretDown aria-hidden className="size-4 text-muted" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={4}
          className="z-50 max-h-72 w-(--radix-select-trigger-width) min-w-40 overflow-hidden rounded-xl border border-border bg-surface shadow-overlay"
        >
          <SelectPrimitive.Viewport className="p-1">
            {options.map((option) => (
              <SelectPrimitive.Item
                key={option.value}
                value={option.value}
                className="flex min-h-11 items-center justify-between gap-2 rounded-lg px-3 body-3 outline-none data-highlighted:bg-primary-tint md:min-h-9 md:body-6"
              >
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
                <SelectPrimitive.ItemIndicator>
                  <Check aria-hidden className="size-4 text-primary-hover" />
                </SelectPrimitive.ItemIndicator>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  )
}
