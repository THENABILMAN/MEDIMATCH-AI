import { SlidersHorizontal } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../ui/button'
import { Sheet } from '../ui/sheet'

interface FilterBarProps {
  activeCount: number
  onClear: () => void
  children: ReactNode
}

/** Inline above results on desktop, a sheet on phones. Filter state lives in the URL. */
export function FilterBar({ activeCount, onClear, children }: FilterBarProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const label = activeCount > 0 ? t('filters.openActive', { count: activeCount }) : t('filters.open')

  return (
    <>
      <div className="hidden items-end gap-3 md:grid md:grid-cols-2 lg:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
        {children}
        <Button variant="ghost" disabled={activeCount === 0} onClick={onClear}>
          {t('filters.clear')}
        </Button>
      </div>
      <div className="md:hidden">
        <Button variant="secondary" className="w-full" onClick={() => setOpen(true)}>
          <SlidersHorizontal aria-hidden className="size-4" strokeWidth={1.75} />
          {label}
        </Button>
        <Sheet
          open={open}
          onOpenChange={setOpen}
          title={t('filters.title')}
          footer={
            <div className="flex gap-2">
              <Button variant="secondary" className="flex-1" disabled={activeCount === 0} onClick={onClear}>
                {t('filters.clear')}
              </Button>
              <Button className="flex-1" onClick={() => setOpen(false)}>
                {t('filters.show')}
              </Button>
            </div>
          }
        >
          <div className="flex flex-col gap-4">{children}</div>
        </Sheet>
      </div>
    </>
  )
}
