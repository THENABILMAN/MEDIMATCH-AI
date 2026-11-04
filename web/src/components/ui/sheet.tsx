import { X } from 'lucide-react'
import { Dialog as DialogPrimitive } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

interface SheetProps extends ComponentProps<typeof DialogPrimitive.Root> {
  title: string
  children: ReactNode
  footer?: ReactNode
}

export function Sheet({ title, children, footer, ...rootProps }: SheetProps) {
  const { t } = useTranslation()
  return (
    <DialogPrimitive.Root {...rootProps}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 animate-fade-in bg-(--scrim)" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed inset-y-0 right-0 z-50 flex w-[min(320px,90vw)] animate-slide-in flex-col bg-surface shadow-overlay"
        >
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-border pl-4 pr-2">
            <DialogPrimitive.Title className="text-md font-semibold">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close
              aria-label={t('common.close')}
              className="flex size-11 items-center justify-center rounded-sm text-muted hover:text-ink"
            >
              <X aria-hidden className="size-5" strokeWidth={1.75} />
            </DialogPrimitive.Close>
          </div>
          <div className="flex-1 overflow-y-auto overscroll-contain p-4">{children}</div>
          {footer && <div className="border-t border-border p-4">{footer}</div>}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
