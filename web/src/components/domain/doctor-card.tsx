import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/cn'
import { formatDateTime } from '../../lib/format'
import type { DoctorProfile } from '../../types'
import { Avatar } from '../ui/avatar'
import { experienceText, feeText, isDirectoryListing } from './doctor-facts'
import { ListingBadge } from './verification-badge'

function specialtyNames(doctor: DoctorProfile): string {
  return doctor.specialties.map((specialty) => specialty.name).join(', ')
}

/** A row in the search results. The whole row is the doctor's link. */
export function DoctorCardCompact({
  doctor,
  soonest,
  searchSuffix = '',
}: {
  doctor: DoctorProfile
  soonest?: string
  searchSuffix?: string
}) {
  const { t, i18n } = useTranslation()
  return (
    <Link
      to={`/doctors/${doctor.id}${searchSuffix}`}
      className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 p-4 transition-colors hover:bg-primary-tint md:grid-cols-[auto_1fr_auto] md:p-4"
    >
      <Avatar name={doctor.full_name ?? ''} />
      <div className="min-w-0">
        <h2 className="heading-5">{doctor.full_name}</h2>
        <p className="text-muted">{specialtyNames(doctor)}</p>
        <p className="body-6 text-muted">
          {[doctor.clinic_name, doctor.city, experienceText(doctor.years_experience, t, i18n.language)]
            .filter(Boolean)
            .join(' · ')}
        </p>
        <div className="mt-1">
          <ListingBadge source={doctor.listing_source} />
        </div>
      </div>
      <div className="col-start-2 md:col-start-3 md:row-start-1 md:text-right">
        <p className="body-1 tabular">
          {isDirectoryListing(doctor)
            ? t('doctor.contactToBook')
            : soonest
              ? formatDateTime(soonest, i18n.language)
              : t('home.indexNoTime')}
        </p>
        <p className="text-muted tabular">
          {doctor.consultation_fee
            ? `${feeText(doctor.consultation_fee, t, i18n.language)} ${t('doctor.perVisit')}`
            : t('doctor.feeNotListed')}
        </p>
      </div>
    </Link>
  )
}

/** The profile on the doctor's own page. */
export function DoctorCardDetailed({ doctor, className }: { doctor: DoctorProfile; className?: string }) {
  const { t, i18n } = useTranslation()
  const directory = isDirectoryListing(doctor)
  const experience = experienceText(doctor.years_experience, t, i18n.language)
  const facts: [string, string][] = [[t('doctor.fee'), feeText(doctor.consultation_fee, t, i18n.language)]]
  if (directory && doctor.specialty_text) facts.push([t('doctor.listedSpecialty'), doctor.specialty_text])
  if (experience) facts.push([t('doctor.experience'), experience])
  if (doctor.designation) facts.push([t('doctor.designation'), doctor.designation])
  const location = [doctor.clinic_name, doctor.city].filter(Boolean).join(', ')
  if (location) facts.push([t('doctor.location'), location])
  if (doctor.qualifications.length > 0) {
    facts.push([t('doctor.qualifications'), doctor.qualifications.join(', ')])
  }
  if (doctor.bmdc_number) facts.push([t('doctor.bmdc'), doctor.bmdc_number])

  return (
    <article className={cn('min-w-0', className)}>
      <div className="flex items-start gap-4">
        <Avatar name={doctor.full_name ?? ''} className="size-14 body-7" />
        <div className="min-w-0">
          <h1 className="heading-4 md:heading-3">{doctor.full_name}</h1>
          <p className="body-7 text-muted">{specialtyNames(doctor)}</p>
          <div className="mt-2">
            <ListingBadge source={doctor.listing_source} />
          </div>
        </div>
      </div>

      {directory && <p className="prose-width mt-4 body-6 text-muted">{t('doctor.directoryNote')}</p>}

      {doctor.bio && <p className="prose-width mt-6 body-3 whitespace-pre-line">{doctor.bio}</p>}

      <dl className="mt-6 border-t border-border">
        {facts.map(([label, value]) => (
          <div key={label} className="grid gap-x-6 border-b border-border py-3 sm:grid-cols-[180px_1fr]">
            <dt className="body-6 text-muted">{label}</dt>
            <dd className="tabular">{value}</dd>
          </div>
        ))}
      </dl>

      {directory && doctor.source_url && (
        <p className="mt-4 body-6 text-muted">
          {t('doctor.source')}{' '}
          <a href={doctor.source_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">
            {t('doctor.sourceLink')}
          </a>
        </p>
      )}
    </article>
  )
}
