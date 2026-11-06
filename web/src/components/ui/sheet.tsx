import { X } from '@phosphor-icons/react'
import { Dialog as DialogPrimitive } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/cn'

interface SheetProps extends ComponentProps<typeof DialogPrimitive.Root> {
  title: string
  children: ReactNode
  footer?: ReactNode
  /** The full screen panel of the site menu, with the icon that replaces the X. */
  fullScreen?: boolean
  closeIcon?: ReactNode
}

export function Sheet({ title, children, footer, fullScreen, closeIcon, ...rootProps }: SheetProps) {
  const { t } = useTranslation()
  return (
    <DialogPrimitive.Root {...rootProps}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 animate-fade-in bg-(--scrim)" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className={cn(
            'fixed inset-y-0 right-0 z-50 flex flex-col',
            fullScreen
              ? 'left-0 animate-fade-in bg-surface/95 backdrop-blur-xl'
              : 'w-[min(320px,90vw)] animate-slide-in bg-surface shadow-overlay'
          )}
        >
          <div
            className={cn(
              'flex h-14 shrink-0 items-center justify-between pl-4 pr-2',
              fullScreen ? 'mt-3' : 'border-b border-border'
            )}
          >
            <DialogPrimitive.Title className="body-1">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close
              aria-label={t('common.close')}
              className="flex size-11 items-center justify-center rounded-lg text-muted hover:text-ink"
            >
              {closeIcon ?? <X aria-hidden className="size-5" />}
            </DialogPrimitive.Close>
          </div>
          <div className="flex-1 overflow-y-auto overscroll-contain p-4">{children}</div>
          {footer && <div className="border-t border-border p-4">{footer}</div>}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
