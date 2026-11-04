import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { formatCurrency, formatDateTime, formatNumber } from '../../lib/format'
import type { DoctorRecommendation } from '../../types'
import { buttonVariants } from '../ui/button'

export function RecommendationList({ recommendations }: { recommendations: DoctorRecommendation[] }) {
  const { t, i18n } = useTranslation()
  return (
    <section aria-label={t('chat.shortlist')} className="mt-3">
      <h2 className="text-md font-semibold">{t('chat.shortlist')}</h2>
      <ol className="mt-2 rounded-md border border-border bg-surface">
        {recommendations.map((doctor, index) => (
          <li
            key={doctor.id}
            data-testid="recommendation"
            className="grid grid-cols-[24px_1fr] gap-x-3 gap-y-2 border-b border-border p-4 last:border-b-0"
          >
            <span aria-hidden className="font-serif text-lg text-muted tabular">
              {formatNumber(index + 1, i18n.language)}
            </span>
            <div className="min-w-0">
              <h3 className="font-semibold">{doctor.full_name}</h3>
              <p className="text-sm text-muted">
                {doctor.specialties.map((specialty) => specialty.name).join(', ')}
                {' · '}
                {[doctor.clinic_name, doctor.city].filter(Boolean).join(', ')}
              </p>
              <p className="mt-1 text-sm">
                <span className="font-medium">{t('chat.whyMatch')}</span> {doctor.match_explanation}
              </p>
              <p className="mt-1 text-sm tabular">
                {doctor.soonest_slot
                  ? t('chat.soonest', { time: formatDateTime(doctor.soonest_slot, i18n.language) })
                  : t('chat.slotsAvailable', { count: doctor.available_slots_count })}
                {' · '}
                {formatCurrency(doctor.consultation_fee, i18n.language)}
              </p>
              <Link
                to={`/doctors/${doctor.id}`}
                className={buttonVariants({ variant: 'secondary', size: 'sm', className: 'mt-2' })}
              >
                {t('chat.viewAndBook')}
              </Link>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
