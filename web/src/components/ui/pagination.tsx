import { CaretLeft, CaretRight } from '@phosphor-icons/react'
import { useTranslation } from 'react-i18next'
import { formatNumber } from '../../lib/format'
import { Button } from './button'

interface PaginationProps {
  page: number
  pageCount: number
  total: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, pageCount, total, onPageChange }: PaginationProps) {
  const { t, i18n } = useTranslation()
  if (pageCount <= 1) return null

  return (
    <nav aria-label={t('common.pagination')} className="flex items-center justify-between gap-3">
      <p className="body-6 text-muted tabular" aria-live="polite">
        {t('common.pageOf', {
          page: formatNumber(page, i18n.language),
          pages: formatNumber(pageCount, i18n.language),
          total: formatNumber(total, i18n.language),
        })}
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          <CaretLeft aria-hidden className="size-4" />
          {t('common.previous')}
        </Button>
        <Button variant="secondary" size="sm" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
          {t('common.next')}
          <CaretRight aria-hidden className="size-4" />
        </Button>
      </div>
    </nav>
  )
}
