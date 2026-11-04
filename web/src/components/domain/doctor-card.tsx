import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/cn'
import { formatCurrency, formatNumber } from '../../lib/format'
import type { DoctorProfile } from '../../types'
import { Avatar } from '../ui/avatar'
import { VerificationBadge } from './verification-badge'

function specialtyNames(doctor: DoctorProfile): string {
  return doctor.specialties.map((specialty) => specialty.name).join(', ')
}

/** A doctor's serial slip: the fee on the stub, the rest on the slip. The whole slip is the link. */
export function DoctorSlip({
  doctor,
  searchSuffix = '',
  headingLevel: Heading = 'h3',
}: {
  doctor: DoctorProfile
  searchSuffix?: string
  headingLevel?: 'h2' | 'h3'
}) {
  const { t, i18n } = useTranslation()
  return (
    <Link
      to={`/doctors/${doctor.id}${searchSuffix}`}
      className="slip-stub group grid grid-cols-[var(--tear)_minmax(0,1fr)] bg-surface transition-transform hover:-translate-y-0.5"
    >
      <div className="on-navy flex flex-col justify-center bg-navy p-3 md:p-5">
        <p className="text-lg font-semibold tabular md:text-xl">
          {formatCurrency(doctor.consultation_fee, i18n.language)}
        </p>
        <p className="text-sm text-muted">{t('doctor.perVisit')}</p>
      </div>
      <div className="flex min-w-0 items-center gap-3 p-4 md:p-5">
        <Avatar name={doctor.full_name ?? ''} className="hidden sm:flex" />
        <div className="min-w-0">
          <Heading className="text-lg font-semibold">{doctor.full_name}</Heading>
          <p>{specialtyNames(doctor)}</p>
          <p className="text-sm text-muted">
            {[doctor.clinic_name, doctor.city].filter(Boolean).join(', ')}
            {' · '}
            {t('doctor.yearsExperience', {
              count: doctor.years_experience,
              years: formatNumber(doctor.years_experience, i18n.language),
            })}
          </p>
        </div>
      </div>
    </Link>
  )
}

/** The profile on the doctor's own page. */
export function DoctorCardDetailed({ doctor, className }: { doctor: DoctorProfile; className?: string }) {
  const { t, i18n } = useTranslation()
  const facts: [string, string][] = [
    [t('doctor.fee'), formatCurrency(doctor.consultation_fee, i18n.language)],
    [
      t('doctor.experience'),
      t('doctor.yearsExperience', {
        count: doctor.years_experience,
        years: formatNumber(doctor.years_experience, i18n.language),
      }),
    ],
    [t('doctor.location'), [doctor.clinic_name, doctor.city].filter(Boolean).join(', ')],
  ]
  if (doctor.qualifications.length > 0) {
    facts.push([t('doctor.qualifications'), doctor.qualifications.join(', ')])
  }

  return (
    <article className={cn('min-w-0', className)}>
      <div className="flex items-start gap-4">
        <Avatar name={doctor.full_name ?? ''} className="size-14 text-lg" />
        <div className="min-w-0">
          <h1 className="display-2">{doctor.full_name}</h1>
          <p className="text-lg text-muted">{specialtyNames(doctor)}</p>
          <div className="mt-2">
            <VerificationBadge status={doctor.verification_status} />
          </div>
        </div>
      </div>

      {doctor.bio && <p className="prose-width mt-6 text-md">{doctor.bio}</p>}

      <dl className="mt-6 border-t border-border">
        {facts.map(([label, value]) => (
          <div key={label} className="grid gap-x-6 border-b border-border py-3 sm:grid-cols-[180px_1fr]">
            <dt className="text-sm text-muted">{label}</dt>
            <dd className="tabular">{value}</dd>
          </div>
        ))}
      </dl>
    </article>
  )
}
