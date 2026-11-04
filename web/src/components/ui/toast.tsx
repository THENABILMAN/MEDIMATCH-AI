import { CheckCircle2, X } from 'lucide-react'
import { Toast as ToastPrimitive } from 'radix-ui'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/cn'

interface ToastMessage {
  id: number
  message: string
  tone: 'success' | 'error'
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastMessage['tone']) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const toast = useCallback((message: string, tone: ToastMessage['tone'] = 'success') => {
    setToasts((current) => [...current, { id: Date.now(), message, tone }])
  }, [])

  const value = useMemo(() => ({ toast }), [toast])

  return (
    <ToastContext.Provider value={value}>
      <ToastPrimitive.Provider duration={6000} label={t('common.notification')}>
        {children}
        {toasts.map((item) => (
          <ToastPrimitive.Root
            key={item.id}
            onOpenChange={(open) => {
              if (!open) setToasts((current) => current.filter((other) => other.id !== item.id))
            }}
            className={cn(
              'flex animate-rise-in items-start gap-2 rounded-md border bg-surface p-3 text-sm shadow-overlay',
              item.tone === 'error' ? 'border-danger' : 'border-border'
            )}
          >
            {item.tone === 'success' && (
              <CheckCircle2 aria-hidden className="mt-0.5 size-4 shrink-0 text-success" strokeWidth={1.75} />
            )}
            <ToastPrimitive.Description className="flex-1">{item.message}</ToastPrimitive.Description>
            <ToastPrimitive.Close aria-label={t('common.close')} className="rounded-sm text-muted hover:text-ink">
              <X aria-hidden className="size-4" strokeWidth={1.75} />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed right-4 bottom-4 left-4 z-50 flex flex-col gap-2 outline-none md:left-auto md:w-96" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}
