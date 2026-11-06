import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { formatCurrency, formatDateTime, formatNumber } from '../../lib/format'
import type { DoctorRecommendation } from '../../types'
import { buttonVariants } from '../ui/button'

export function RecommendationList({ recommendations }: { recommendations: DoctorRecommendation[] }) {
  const { t, i18n } = useTranslation()
  return (
    <section aria-label={t('chat.shortlist')} className="mt-4">
      <h2 className="heading-5">{t('chat.shortlist')}</h2>
      <ol className="mt-2 rounded-xl border border-border bg-surface">
        {recommendations.map((doctor, index) => (
          <li
            key={doctor.id}
            data-testid="recommendation"
            className="grid grid-cols-[32px_1fr] gap-x-3 border-b border-border p-4 last:border-b-0"
          >
            <span aria-hidden className="heading-4 text-muted tabular">
              {formatNumber(index + 1, i18n.language)}
            </span>
            <div className="min-w-0">
              <h3 className="heading-5">{doctor.full_name}</h3>
              <p className="body-6 text-muted">
                {doctor.specialties.map((specialty) => specialty.name).join(', ')}
                {' · '}
                {[doctor.clinic_name, doctor.city].filter(Boolean).join(', ')}
              </p>
              <p className="mt-1 body-6">
                <span className="body-5">{t('chat.whyMatch')}</span> {doctor.match_explanation}
              </p>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <p className="body-2 tabular">
                  {doctor.soonest_slot
                    ? t('chat.soonest', { time: formatDateTime(doctor.soonest_slot, i18n.language) })
                    : t('chat.slotsAvailable', { count: doctor.available_slots_count })}
                  {' · '}
                  {formatCurrency(doctor.consultation_fee, i18n.language)}
                </p>
                <Link to={`/doctors/${doctor.id}`} className={buttonVariants({ size: 'sm' })}>
                  {t('chat.viewAndBook')}
                </Link>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
