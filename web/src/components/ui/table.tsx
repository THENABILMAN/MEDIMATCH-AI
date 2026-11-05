import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import type { ComponentProps } from 'react'
import { cn } from '../../lib/cn'

interface TableProps extends ComponentProps<'table'> {
  caption: string
  /** Lets keyboard users scroll a wide table. */
  scrollLabel?: string
}

export function Table({ caption, scrollLabel, className, children, ...props }: TableProps) {
  return (
    <div
      className="max-h-[70dvh] overflow-auto rounded-md border border-border bg-surface"
      tabIndex={0}
      role="region"
      aria-label={scrollLabel ?? caption}
    >
      <table className={cn('w-full border-collapse text-left text-sm', className)} {...props}>
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  )
}

export function TableHead(props: ComponentProps<'thead'>) {
  return <thead className="sticky top-0 z-10 bg-surface shadow-[inset_0_-1px_0_var(--border)]" {...props} />
}

export function TableBody(props: ComponentProps<'tbody'>) {
  return <tbody className="[&>tr:last-child]:border-b-0" {...props} />
}

export function TableRow({ className, ...props }: ComponentProps<'tr'>) {
  return (
    <tr
      className={cn('border-b border-border transition-colors hover:bg-primary-tint', className)}
      {...props}
    />
  )
}

export function TableCell({ className, ...props }: ComponentProps<'td'>) {
  return <td className={cn('h-10 px-3 py-2 align-middle', className)} {...props} />
}

export function TableHeader({ className, ...props }: ComponentProps<'th'>) {
  return (
    <th
      scope="col"
      className={cn('h-10 px-3 text-xs font-medium whitespace-nowrap text-muted', className)}
      {...props}
    />
  )
}

export type SortDirection = 'ascending' | 'descending'

interface SortableHeaderProps extends Omit<ComponentProps<'th'>, 'onClick'> {
  direction?: SortDirection
  onSort: () => void
  numeric?: boolean
}

export function SortableHeader({ direction, onSort, numeric, children, className, ...props }: SortableHeaderProps) {
  const Icon = direction === 'ascending' ? ArrowUp : direction === 'descending' ? ArrowDown : ArrowUpDown
  return (
    <TableHeader aria-sort={direction ?? 'none'} className={cn('p-0', className)} {...props}>
      <button
        type="button"
        onClick={onSort}
        className={cn(
          'flex h-10 w-full items-center gap-1 px-3 font-medium hover:text-ink',
          numeric && 'justify-end',
          direction && 'text-ink'
        )}
      >
        {children}
        <Icon aria-hidden className="size-3.5" strokeWidth={1.75} />
      </button>
    </TableHeader>
  )
}
