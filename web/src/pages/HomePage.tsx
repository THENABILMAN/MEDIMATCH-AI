import { ArrowRight } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useDoctorSearch, useDoctorsSlots } from '../api/hooks'
import { ProductStage } from '../components/domain/product-stage'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/input'
import { Skeleton } from '../components/ui/skeleton'
import { cn } from '../lib/cn'
import { EMERGENCY_NUMBER } from '../lib/constants'
import { saveDraft } from '../lib/draft'
import { formatCurrency, formatDateTime, formatNumber } from '../lib/format'
import { nextOpenSlot } from '../lib/slots'
import type { DoctorProfile } from '../types'

const STEPS = ['describe', 'clarify', 'choose', 'book'] as const
const CHECKS = ['license', 'review', 'recheck'] as const
const QUESTIONS = ['diagnose', 'emergency', 'language', 'privacy', 'fee', 'join'] as const
const INDEX_SIZE = 8
const ALL = ''

function Composer({ id }: { id: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [text, setText] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim()) saveDraft(text.trim())
    navigate('/chat')
  }

  return (
    <form onSubmit={submit} className="on-paper rounded-md bg-surface p-3">
      <label htmlFor={id} className="sr-only">
        {t('home.inputLabel')}
      </label>
      <Textarea
        id={id}
        rows={2}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={t('home.inputPlaceholder')}
        autoComplete="off"
        className="resize-none border-0 text-lg hover:border-0"
      />
      <div className="mt-2 flex justify-end">
        <Button type="submit" size="lg" className="w-full sm:w-auto">
          {t('home.startChat')}
          <ArrowRight aria-hidden className="size-4" strokeWidth={1.75} />
        </Button>
      </div>
    </form>
  )
}

/** Tracks which step of the story is in the middle of the screen. */
function useActiveStep() {
  const [active, setActive] = useState(0)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const steps = root.current?.querySelectorAll<HTMLElement>('[data-step]')
    if (!steps?.length) return
    const observer = new IntersectionObserver(
      (entries) => {
        entries
          .filter((entry) => entry.isIntersecting)
          .forEach((entry) => setActive(Number((entry.target as HTMLElement).dataset.step)))
      },
      { rootMargin: '-45% 0px -45% 0px' }
    )
    steps.forEach((step) => observer.observe(step))
    return () => observer.disconnect()
  }, [])

  return { active, root }
}

function Stage() {
  const { t } = useTranslation()
  const { active, root } = useActiveStep()
  return (
    <div ref={root} className="on-ink bg-ink-field">
      <div className="home-gutter grid lg:grid-cols-[minmax(0,1fr)_420px] lg:gap-x-8 xl:grid-cols-[minmax(0,1fr)_520px] xl:gap-x-16">
        <div>
          <section
            aria-labelledby="home-title"
            data-step={0}
            className="flex flex-col justify-center gap-6 py-12 lg:min-h-[calc(100dvh-var(--header-height))]"
          >
            <h1 id="home-title" className="hero-title font-serif">
              <span className="block">{t('home.titleFirst')}</span>
              <span className="block">{t('home.titleSecond')}</span>
            </h1>
            <p className="max-w-[56ch] text-lg">{t('home.lead')}</p>
            <div className="max-w-[640px]">
              <Composer id="home-input" />
            </div>
            <p className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted">
              <Link to="/doctors" className="font-medium text-ink underline underline-offset-4">
                {t('home.browse')}
              </Link>
              {t('home.emergency', { number: EMERGENCY_NUMBER })}
            </p>
          </section>

          <section aria-labelledby="how-title" className="pb-16 lg:pb-[30vh]">
            <h2 id="how-title" className="font-serif text-2xl md:text-3xl">
              {t('home.howTitle')}
            </h2>
            <ol className="mt-4 flex flex-col">
              {STEPS.map((step, index) => (
                <li
                  key={step}
                  data-step={index}
                  className={cn(
                    'flex flex-col justify-center gap-3 py-8 transition-opacity lg:min-h-[64vh]',
                    index !== active && 'lg:opacity-50'
                  )}
                >
                  <p aria-hidden className="font-serif text-3xl text-muted tabular">
                    {index + 1}
                  </p>
                  <h3 className="font-serif text-2xl md:text-3xl">{t(`home.steps.${step}.title`)}</h3>
                  <p className="max-w-[46ch] text-lg">{t(`home.steps.${step}.body`)}</p>
                  <ProductStage step={index} compact className="mt-3 lg:hidden" />
                </li>
              ))}
            </ol>
          </section>
        </div>

        <div className="relative hidden lg:block">
          <div className="sticky top-[var(--header-height)] flex h-[calc(100dvh-var(--header-height))] items-center py-8">
            <ProductStage step={active} className="h-full max-h-[720px] w-full" />
          </div>
        </div>
      </div>
    </div>
  )
}

function IndexRow({ doctor, soonest }: { doctor: DoctorProfile; soonest?: string }) {
  const { t, i18n } = useTranslation()
  return (
    <li className="border-b border-border">
      <Link
        to={`/doctors/${doctor.id}`}
        className="group grid gap-x-6 gap-y-1 py-4 transition-colors hover:bg-primary-tint md:grid-cols-[minmax(0,5fr)_minmax(0,3fr)_minmax(0,3fr)_auto] md:items-baseline md:px-3"
      >
        <span>
          <span className="block font-serif text-xl">{doctor.full_name}</span>
          <span className="block text-muted">
            {doctor.specialties.map((item) => item.name).join(', ')}
          </span>
        </span>
        <span className="text-muted">{[doctor.clinic_name, doctor.city].filter(Boolean).join(', ')}</span>
        <span className="tabular">{soonest ? formatDateTime(soonest, i18n.language) : t('home.indexNoTime')}</span>
        <span className="font-serif text-xl tabular md:text-right">
          {formatCurrency(doctor.consultation_fee, i18n.language)}
        </span>
      </Link>
    </li>
  )
}

function DoctorIndex() {
  const { t, i18n } = useTranslation()
  const { data, isPending, isError } = useDoctorSearch({ page_size: 50 })
  const [specialty, setSpecialty] = useState(ALL)

  const doctors = useMemo(() => data?.items ?? [], [data])
  const specialties = useMemo(
    () => [...new Set(doctors.flatMap((doctor) => doctor.specialties.map((item) => item.name)))].sort(),
    [doctors]
  )
  const cities = useMemo(() => new Set(doctors.flatMap((doctor) => doctor.city ?? [])), [doctors])
  const shown = doctors
    .filter((doctor) => specialty === ALL || doctor.specialties.some((item) => item.name === specialty))
    .slice(0, INDEX_SIZE)
  const slots = useDoctorsSlots(shown.map((doctor) => doctor.id))

  const counts = [
    [data?.total ?? 0, 'home.countDoctors'],
    [specialties.length, 'home.countSpecialties'],
    [cities.size, 'home.countCities'],
  ] as const

  return (
    <section aria-labelledby="index-title" className="bg-surface py-16 md:py-24">
      <div className="home-gutter">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <h2 id="index-title" className="font-serif text-3xl md:text-4xl">
              {t('home.indexTitle')}
            </h2>
            <p className="mt-3 max-w-[56ch] text-lg text-muted">{t('home.indexLead')}</p>
          </div>
          {data && (
            <dl className="flex gap-8">
              {counts.map(([count, label]) => (
                <div key={label}>
                  <dd className="font-serif text-3xl tabular">{formatNumber(count, i18n.language)}</dd>
                  <dt className="text-sm text-muted">{t(label, { count })}</dt>
                </div>
              ))}
            </dl>
          )}
        </div>

        <div role="group" aria-label={t('search.specialty')} className="mt-8 flex flex-wrap gap-2">
          {[ALL, ...specialties].map((name) => (
            <Button
              key={name || 'all'}
              variant={name === specialty ? 'primary' : 'secondary'}
              size="sm"
              aria-pressed={name === specialty}
              onClick={() => setSpecialty(name)}
            >
              {name || t('home.indexAll')}
            </Button>
          ))}
        </div>

        <div className="mt-6 border-t-2 border-ink">
          {isPending && <Skeleton className="mt-4 h-64 w-full" />}
          {isError && <p className="py-6">{t('home.indexUnavailable')}</p>}
          {data && doctors.length === 0 && <p className="py-6">{t('home.indexEmpty')}</p>}
          <ul data-ui>
            {shown.map((doctor, index) => (
              <IndexRow key={doctor.id} doctor={doctor} soonest={nextOpenSlot(slots[index]?.data)?.start_time} />
            ))}
          </ul>
        </div>

        <Button asChild variant="secondary" size="lg" className="mt-8">
          <Link to="/doctors">{t('home.indexMore')}</Link>
        </Button>
      </div>
    </section>
  )
}

function Checks() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="checks-title" className="home-gutter py-16 md:py-24">
      <h2 id="checks-title" className="font-serif text-3xl md:text-4xl">
        {t('home.checksTitle')}
      </h2>
      <dl className="mt-10 grid gap-8 md:grid-cols-3 md:gap-12">
        {CHECKS.map((check) => (
          <div key={check}>
            <dt className="font-serif text-xl">{t(`home.checks.${check}.title`)}</dt>
            <dd className="mt-2 text-lg text-muted">{t(`home.checks.${check}.body`)}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function Questions() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="questions-title" className="home-gutter pb-16 md:pb-24">
      <h2 id="questions-title" className="font-serif text-3xl md:text-4xl">
        {t('home.questionsTitle')}
      </h2>
      <dl className="mt-10 grid gap-x-12 gap-y-8 md:grid-cols-2">
        {QUESTIONS.map((question) => (
          <div key={question}>
            <dt className="font-serif text-xl">{t(`home.questions.${question}.q`)}</dt>
            <dd className="mt-2 text-lg text-muted">
              {t(`home.questions.${question}.a`, { number: EMERGENCY_NUMBER })}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function Closing() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="start-title" className="on-ink bg-ink-field py-16 md:py-24">
      <div className="home-gutter grid gap-8 lg:grid-cols-2 lg:items-center">
        <div>
          <h2 id="start-title" className="font-serif text-3xl md:text-4xl">
            {t('home.startTitle')}
          </h2>
          <p className="mt-3 max-w-[46ch] text-lg">{t('home.startLead')}</p>
        </div>
        <Composer id="closing-input" />
      </div>
      <footer className="home-gutter mt-16 flex flex-col gap-3 text-sm text-muted md:flex-row md:justify-between">
        <p>{t('home.footer')}</p>
        <Link to="/register?role=doctor" className="font-medium whitespace-nowrap text-ink underline underline-offset-4">
          {t('home.forDoctors')}
        </Link>
      </footer>
    </section>
  )
}

export default function HomePage() {
  return (
    <>
      <Stage />
      <DoctorIndex />
      <Checks />
      <Questions />
      <Closing />
    </>
  )
}
