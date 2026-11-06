import { X } from '@phosphor-icons/react'
import { Dialog as DialogPrimitive } from 'radix-ui'
import type { ComponentProps, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/cn'
import { Button } from './button'

interface DialogProps extends ComponentProps<typeof DialogPrimitive.Root> {
  title: string
  description?: ReactNode
  footer?: ReactNode
  children?: ReactNode
}

export function Dialog({ title, description, footer, children, ...rootProps }: DialogProps) {
  const { t } = useTranslation()
  return (
    <DialogPrimitive.Root {...rootProps}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 animate-fade-in bg-(--scrim)" />
        <DialogPrimitive.Content
          className="fixed inset-x-4 top-1/2 z-50 mx-auto max-h-[85dvh] max-w-lg -translate-y-1/2 animate-fade-in overflow-y-auto overscroll-contain rounded-xl bg-surface p-6 shadow-overlay"
        >
          <div className="flex items-start justify-between gap-4">
            <DialogPrimitive.Title className="title-2">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Close
              aria-label={t('common.close')}
              className="-m-2 flex size-10 shrink-0 items-center justify-center rounded-lg text-muted hover:text-ink"
            >
              <X aria-hidden className="size-5" />
            </DialogPrimitive.Close>
          </div>
          <DialogPrimitive.Description className={cn('mt-2 body-3 text-muted', !description && 'sr-only')}>
            {description ?? title}
          </DialogPrimitive.Description>
          {children && <div className="mt-4">{children}</div>}
          {footer && <div className="mt-6 flex flex-col-reverse gap-2 md:flex-row md:justify-end">{footer}</div>}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: ReactNode
  confirmLabel: string
  cancelLabel: string
  onConfirm: () => void
  loading?: boolean
  destructive?: boolean
  children?: ReactNode
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  onConfirm,
  loading,
  destructive = true,
  children,
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      footer={
        <>
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={destructive ? 'danger' : 'primary'} loading={loading} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      {children}
    </Dialog>
  )
}
