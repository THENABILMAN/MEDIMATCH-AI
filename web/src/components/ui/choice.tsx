import { Check } from '@phosphor-icons/react'
import { Checkbox as CheckboxPrimitive, RadioGroup as RadioPrimitive, Switch as SwitchPrimitive } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { useId } from 'react'
import { cn } from '../../lib/cn'

const rowClasses = 'flex min-h-11 items-start gap-3 py-2 body-3 md:min-h-0 md:body-6'

interface CheckboxProps extends ComponentProps<typeof CheckboxPrimitive.Root> {
  label: ReactNode
}

export function Checkbox({ label, id, className, ...props }: CheckboxProps) {
  const generated = useId()
  const controlId = id ?? generated
  return (
    <label htmlFor={controlId} className={cn(rowClasses, 'cursor-pointer', className)}>
      <CheckboxPrimitive.Root
        id={controlId}
        className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-sm border border-control bg-surface transition-colors hover:border-ink disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary data-[state=checked]:bg-primary"
        {...props}
      >
        <CheckboxPrimitive.Indicator>
          <Check aria-hidden className="size-4 text-white" />
        </CheckboxPrimitive.Indicator>
      </CheckboxPrimitive.Root>
      <span>{label}</span>
    </label>
  )
}

interface RadioOption {
  value: string
  label: string
  description?: string
}

interface RadioGroupProps extends ComponentProps<typeof RadioPrimitive.Root> {
  options: RadioOption[]
}

export function RadioGroup({ options, className, ...props }: RadioGroupProps) {
  const groupId = useId()
  return (
    <RadioPrimitive.Root className={cn('flex flex-col', className)} {...props}>
      {options.map((option) => {
        const id = `${groupId}-${option.value}`
        return (
          <label key={option.value} htmlFor={id} className={cn(rowClasses, 'cursor-pointer')}>
            <RadioPrimitive.Item
              id={id}
              value={option.value}
              className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-control bg-surface transition-colors hover:border-ink disabled:opacity-50 data-[state=checked]:border-primary"
            >
              <RadioPrimitive.Indicator className="size-2.5 rounded-full bg-primary" />
            </RadioPrimitive.Item>
            <span>
              <span className="block">{option.label}</span>
              {option.description && <span className="block body-6 text-muted">{option.description}</span>}
            </span>
          </label>
        )
      })}
    </RadioPrimitive.Root>
  )
}

interface SwitchProps extends ComponentProps<typeof SwitchPrimitive.Root> {
  label: ReactNode
  description?: string
}

export function Switch({ label, description, id, className, ...props }: SwitchProps) {
  const generated = useId()
  const controlId = id ?? generated
  return (
    <label htmlFor={controlId} className={cn(rowClasses, 'cursor-pointer justify-between', className)}>
      <span>
        <span className="block">{label}</span>
        {description && <span className="block body-6 text-muted">{description}</span>}
      </span>
      <SwitchPrimitive.Root
        id={controlId}
        className="relative mt-0.5 h-6 w-10 shrink-0 rounded-full border border-control bg-surface transition-colors disabled:opacity-50 data-[state=checked]:border-primary data-[state=checked]:bg-primary"
        {...props}
      >
        <SwitchPrimitive.Thumb className="block size-4 translate-x-1 rounded-full bg-control transition-transform data-[state=checked]:translate-x-[18px] data-[state=checked]:bg-white" />
      </SwitchPrimitive.Root>
    </label>
  )
}
