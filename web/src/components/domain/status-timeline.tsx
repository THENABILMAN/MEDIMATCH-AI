import { useTranslation } from 'react-i18next'
import { formatDateTime } from '../../lib/format'
import type { VerificationEvent } from '../../types'

export function StatusTimeline({ events }: { events: VerificationEvent[] }) {
  const { t, i18n } = useTranslation()
  return (
    <ol className="border-l border-control pl-6">
      {[...events].reverse().map((event) => (
        <li key={`${event.action}-${event.created_at}`} className="relative pb-6 last:pb-0">
          <span aria-hidden className="absolute top-1.5 -left-[29px] size-2.5 rounded-full bg-primary" />
          <p className="body-2">{t(`verification.event.${event.action}`, { defaultValue: event.action })}</p>
          <p className="body-6 text-muted tabular">{formatDateTime(event.created_at, i18n.language)}</p>
          {event.reason && <p className="prose-width mt-1">{t('verification.reason', { reason: event.reason })}</p>}
        </li>
      ))}
    </ol>
  )
}
