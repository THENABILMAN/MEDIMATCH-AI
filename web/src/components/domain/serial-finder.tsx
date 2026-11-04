import { ArrowRight } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useDoctorSearch, useDoctorsSlots } from '../../api/hooks'
import { formatCurrency, formatDateTime } from '../../lib/format'
import type { AvailabilitySlot, DoctorProfile } from '../../types'
import { Button } from '../ui/button'
import { Select } from '../ui/select'
import { Skeleton } from '../ui/skeleton'

const ANY = 'any'

const CANDIDATES = 6

function nextOpen(slots: AvailabilitySlot[] = []): AvailabilitySlot | undefined {
  return slots
    .filter((slot) => !slot.is_booked && new Date(slot.start_time) > new Date())
    .sort((a, b) => a.start_time.localeCompare(b.start_time))[0]
}

function Result({ doctor, slot }: { doctor: DoctorProfile; slot?: AvailabilitySlot }) {
  const { t, i18n } = useTranslation()
  return (
    <div className="rise-in">
      <p className="text-xl font-semibold">{doctor.full_name}</p>
      <p className="text-muted">
        {[doctor.specialties[0]?.name, doctor.clinic_name, doctor.city].filter(Boolean).join(' · ')}
      </p>
      <dl className="mt-4 grid grid-cols-[minmax(0,1fr)_auto] gap-x-4">
        <div>
          <dt className="text-sm text-muted">{t('home.finder.next')}</dt>
          <dd className="font-semibold tabular">
            {slot ? formatDateTime(slot.start_time, i18n.language) : t('home.finder.noTime')}
          </dd>
        </div>
        <div className="text-right">
          <dt className="text-sm text-muted">{t('doctor.fee')}</dt>
          <dd className="font-semibold tabular">{formatCurrency(doctor.consultation_fee, i18n.language)}</dd>
        </div>
      </dl>
      <Button asChild className="mt-4 w-full">
        <Link to={`/doctors/${doctor.id}`}>
          {t('home.finder.open')}
          <ArrowRight aria-hidden className="size-4" strokeWidth={2} />
        </Link>
      </Button>
    </div>
  )
}

/** The hero's slip. Choices fill it with a doctor who is really on the register. */
export function SerialFinder() {
  const { t } = useTranslation()
  const { data, isPending, isError } = useDoctorSearch({ page_size: 50 })
  const [specialty, setSpecialty] = useState(ANY)
  const [city, setCity] = useState(ANY)

  const doctors = useMemo(() => data?.items ?? [], [data])
  const specialties = useMemo(
    () => [...new Set(doctors.flatMap((doctor) => doctor.specialties.map((item) => item.name)))].sort(),
    [doctors]
  )
  const cities = useMemo(
    () => [...new Set(doctors.map((doctor) => doctor.city).filter((item): item is string => Boolean(item)))].sort(),
    [doctors]
  )
  const matches = doctors
    .filter(
      (doctor) =>
        (specialty === ANY || doctor.specialties.some((item) => item.name === specialty)) &&
        (city === ANY || doctor.city === city)
    )
    .slice(0, CANDIDATES)
  const slots = useDoctorsSlots(matches.map((doctor) => doctor.id))
  const loading = isPending || slots.some((query) => query.isPending)
  const open = slots.map((query) => nextOpen(query.data))
  // A doctor with a time to book is a better answer than one without
  const best = Math.max(
    open.findIndex((slot) => slot),
    0
  )
  const match = matches.at(best)

  return (
    <section aria-labelledby="finder-title" className="slip w-full bg-surface">
      <div className="px-6 pt-6 pb-5">
        <h2 id="finder-title" className="text-xl font-semibold">
          {t('home.finder.title')}
        </h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Select
            aria-label={t('home.finder.specialty')}
            value={specialty}
            onValueChange={setSpecialty}
            disabled={isPending || isError}
            options={[
              { value: ANY, label: t('home.finder.anySpecialty') },
              ...specialties.map((name) => ({ value: name, label: name })),
            ]}
          />
          <Select
            aria-label={t('home.finder.city')}
            value={city}
            onValueChange={setCity}
            disabled={isPending || isError}
            options={[
              { value: ANY, label: t('home.finder.anyCity') },
              ...cities.map((name) => ({ value: name, label: name })),
            ]}
          />
        </div>
      </div>

      <div aria-live="polite" className="border-t-2 border-dashed border-border px-6 pt-5 pb-6">
        {loading && <Skeleton className="h-44 w-full" />}
        {!loading && match && <Result key={match.id} doctor={match} slot={open[best]} />}
        {!loading && !match && (
          <p>
            {isError ? t('home.finder.unavailable') : t('home.finder.none')}{' '}
            <Link to="/doctors" className="font-medium underline underline-offset-4">
              {t('home.browse')}
            </Link>
          </p>
        )}
      </div>
    </section>
  )
}
