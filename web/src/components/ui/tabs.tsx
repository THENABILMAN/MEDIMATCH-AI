import { Tabs as TabsPrimitive } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface TabsProps {
  tabs: { value: string; label: string }[]
  value: string
  onValueChange: (value: string) => void
  className?: string
  children: ReactNode
}

/** Only the active panel renders, so a page can drive tabs from the URL. */
export function Tabs({ tabs, value, onValueChange, className, children }: TabsProps) {
  return (
    <TabsPrimitive.Root value={value} onValueChange={onValueChange} className={className}>
      <TabsList className="mb-4">
        {tabs.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      {tabs.map((tab) => (
        <TabsPrimitive.Content key={tab.value} value={tab.value} tabIndex={-1} className="outline-none">
          {tab.value === value && children}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  )
}

function TabsList({ className, ...props }: ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn('flex gap-1 overflow-x-auto border-b border-border', className)}
      {...props}
    />
  )
}

function TabsTrigger({ className, ...props }: ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        '-mb-px min-h-11 whitespace-nowrap border-b-2 border-transparent px-3 body-5 text-muted transition-colors hover:text-ink data-[state=active]:border-primary data-[state=active]:text-ink',
        className
      )}
      {...props}
    />
  )
}
