import { Check, ChevronDown, X } from 'lucide-react'
import { Popover as PopoverPrimitive } from 'radix-ui'
import { useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { cn } from '../../lib/cn'
import { controlClasses } from './input'
import type { SelectOption } from './select'

interface ComboboxProps {
  id?: string
  value: string
  onValueChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  emptyMessage: string
  clearLabel: string
  className?: string
  'aria-label'?: string
  'aria-describedby'?: string
  'aria-invalid'?: true
}

export function Combobox({
  id,
  value,
  onValueChange,
  options,
  placeholder,
  emptyMessage,
  clearLabel,
  className,
  ...inputProps
}: ComboboxProps) {
  const listId = useId()
  const anchorRef = useRef<HTMLDivElement>(null)
  const selected = options.find((option) => option.value === value)
  const [query, setQuery] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const visible = useMemo(() => {
    const needle = (query ?? '').trim().toLowerCase()
    return needle ? options.filter((o) => o.label.toLowerCase().includes(needle)) : options
  }, [options, query])

  function choose(option: SelectOption) {
    onValueChange(option.value)
    setQuery(null)
    setOpen(false)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      setOpen(true)
      const step = event.key === 'ArrowDown' ? 1 : -1
      setActiveIndex((index) => (index + step + visible.length) % Math.max(visible.length, 1))
    } else if (event.key === 'Enter' && open && visible[activeIndex]) {
      event.preventDefault()
      choose(visible[activeIndex])
    } else if (event.key === 'Escape') {
      setOpen(false)
      setQuery(null)
    }
  }

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Anchor asChild>
        <div ref={anchorRef} className={cn('relative', className)}>
          <input
            id={id}
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={open && visible[activeIndex] ? `${listId}-${activeIndex}` : undefined}
            autoComplete="off"
            value={query ?? selected?.label ?? ''}
            placeholder={placeholder}
            onChange={(event) => {
              setQuery(event.target.value)
              setActiveIndex(0)
              setOpen(true)
            }}
            onClick={() => setOpen(true)}
            onKeyDown={onKeyDown}
            className={cn(controlClasses, 'h-11 px-3 pr-16 md:h-10')}
            {...inputProps}
          />
          <div className="absolute inset-y-0 right-0 flex items-center">
            {selected && (
              <button
                type="button"
                aria-label={clearLabel}
                onClick={() => onValueChange('')}
                className="flex size-10 items-center justify-center rounded-sm text-muted hover:text-ink"
              >
                <X aria-hidden className="size-4" strokeWidth={1.75} />
              </button>
            )}
            {!selected && (
              <ChevronDown aria-hidden className="mr-3 size-4 text-muted" strokeWidth={1.75} />
            )}
          </div>
        </div>
      </PopoverPrimitive.Anchor>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          sideOffset={4}
          onOpenAutoFocus={(event) => event.preventDefault()}
          onInteractOutside={(event) => {
            if (anchorRef.current?.contains(event.target as Node)) event.preventDefault()
          }}
          className="z-50 max-h-72 w-(--radix-popover-trigger-width) overflow-y-auto rounded-md border border-border bg-surface p-1 shadow-overlay"
        >
          <ul id={listId} role="listbox" aria-label={inputProps['aria-label'] ?? placeholder}>
            {visible.map((option, index) => (
              <li
                key={option.value}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={option.value === value}
                onPointerEnter={() => setActiveIndex(index)}
                onClick={() => choose(option)}
                className={cn(
                  'flex min-h-11 cursor-pointer items-center justify-between gap-2 rounded-sm px-3 text-md md:min-h-9 md:text-sm',
                  index === activeIndex && 'bg-primary-tint'
                )}
              >
                {option.label}
                {option.value === value && (
                  <Check aria-hidden className="size-4 text-primary-hover" strokeWidth={1.75} />
                )}
              </li>
            ))}
            {visible.length === 0 && <li className="px-3 py-2 text-sm text-muted">{emptyMessage}</li>}
          </ul>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}
