import {
  ArrowRight,
  ChatText,
  ClockCountdown,
  ListChecks,
  SealCheck,
  ShieldWarning,
  type Icon,
} from '@phosphor-icons/react'
import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useDoctorSearch, useDoctorsSlots } from '../api/hooks'
import { ProductStage } from '../components/domain/product-stage'
import { Reveal, TaglineReveal, useScrollProgress } from '../components/domain/reveal'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/input'
import { Skeleton } from '../components/ui/skeleton'
import { cn } from '../lib/cn'
import { EMERGENCY_NUMBER } from '../lib/constants'
import { saveDraft } from '../lib/draft'
import { formatCurrency, formatDateTime, formatNumber } from '../lib/format'
import { nextOpenSlot } from '../lib/slots'
import type { DoctorProfile } from '../types'

const BENEFITS: { key: string; icon: Icon }[] = [
  { key: 'words', icon: ChatText },
  { key: 'questions', icon: ListChecks },
  { key: 'warning', icon: ShieldWarning },
  { key: 'verified', icon: SealCheck },
  { key: 'upfront', icon: ClockCountdown },
]
// Each step shows the moment of the chat it describes
const STEPS = [
  { key: 'describe', stage: 1 },
  { key: 'choose', stage: 2 },
  { key: 'book', stage: 3 },
] as const
const CHECKS = ['license', 'review', 'recheck'] as const
const QUESTIONS = ['diagnose', 'emergency', 'language', 'privacy', 'fee', 'account', 'cancel', 'join'] as const
const PROMISES = ['payment', 'cancel', 'erase'] as const
const INDEX_SIZE = 8
const ALL = ''

// Both are read from a box that does not move with the animation
const throughHero = (box: DOMRect) => -box.top / box.height
const throughPinnedStage = (box: DOMRect, screenHeight: number) => -box.top / (box.height - screenHeight)

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
    <form onSubmit={submit} className="rounded-2xl border border-control bg-surface p-2">
      <label htmlFor={id} className="title-2 block px-2 pt-1">
        {t('home.inputLabel')}
      </label>
      <Textarea
        id={id}
        rows={2}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={t('home.inputPlaceholder')}
        autoComplete="off"
        className="mt-1 min-h-16 resize-none border-transparent"
      />
      <div className="mt-2 flex justify-end">
        <Button type="submit" size="lg" className="w-full sm:w-auto">
          {t('home.startChat')}
          <ArrowRight aria-hidden className="size-4" />
        </Button>
      </div>
    </form>
  )
}

function Hero() {
  const { t } = useTranslation()
  const root = useScrollProgress<HTMLDivElement>('--hero', throughHero)
  return (
    <div ref={root}>
    <section aria-labelledby="home-title" className="hero-scroll mx-3 mt-3 rounded-2xl bg-surface pt-20 md:mx-6">
      <div className="home-gutter grid items-center gap-12 py-12 lg:min-h-[calc(100dvh-var(--header-height))] lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)] lg:gap-16">
        <div className="flex max-w-[680px] flex-col gap-6">
          <h1 id="home-title" className="hero-gradient heading-4 pb-1 sm:heading-2 lg:heading-1">
            <span className="block">{t('home.titleFirst')}</span>
            <span className="block">{t('home.titleSecond')}</span>
          </h1>
          <p className="body-7">{t('home.lead')}</p>
          <Composer id="home-input" />
          <div className="flex flex-col gap-2">
            <p className="body-5 flex items-start gap-2">
              <SealCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-primary-hover" />
              {t('home.proof')}
            </p>
            <p className="body-6 text-muted">{t('home.emergency', { number: EMERGENCY_NUMBER })}</p>
          </div>
        </div>
        <ProductStage step={1} />
      </div>
    </section>
    </div>
  )
}

function Problem() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="problem-title" className="py-16 md:py-24">
      <Reveal className="home-gutter grid gap-6 lg:grid-cols-2 lg:gap-16">
        <h2 id="problem-title" className="heading-3 md:heading-2">
          {t('home.problemTitle')}
        </h2>
        <p className="body-7 max-w-[56ch]">{t('home.problemBody')}</p>
      </Reveal>
    </section>
  )
}

function Benefits() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="benefits-title" className="bg-surface py-16 md:py-24">
      <Reveal className="home-gutter grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <h2 id="benefits-title" className="heading-4 md:heading-3">
          {t('home.benefitsTitle')}
        </h2>
        <ul className="flex flex-col">
          {BENEFITS.map(({ key, icon: BenefitIcon }, index) => (
            <li
              key={key}
              style={{ '--order': index } as CSSProperties}
              className="reveal-item flex gap-4 border-b border-border py-4 first:pt-0 last:border-b-0"
            >
              <BenefitIcon aria-hidden className="mt-0.5 size-6 shrink-0 text-primary-hover" />
              <p className="body-7">
                <strong className="title-2">{t(`home.benefits.${key}.title`)}.</strong>{' '}
                <span className="text-muted">{t(`home.benefits.${key}.body`)}</span>
              </p>
            </li>
          ))}
        </ul>
      </Reveal>
    </section>
  )
}

function Tagline() {
  const { t } = useTranslation()
  return (
    <section aria-label={t('home.taglineLabel')} className="py-24">
      <div className="home-gutter">
        <TaglineReveal lines={[t('home.taglineFirst'), t('home.taglineSecond')]} />
      </div>
    </section>
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

function HowItWorks() {
  const { t } = useTranslation()
  const { active, root } = useActiveStep()
  const section = useScrollProgress<HTMLElement>('--how', throughPinnedStage)
  return (
    <section ref={section} aria-labelledby="how-title" className="bg-primary-tint py-16 md:py-24">
      <div
        ref={root}
        className="home-gutter grid lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)] lg:gap-x-16"
      >
        <div>
          <h2 id="how-title" className="heading-4 md:heading-3">
            {t('home.howTitle')}
          </h2>
          <ol className="mt-4 flex flex-col">
            {STEPS.map(({ key, stage }, index) => (
              <li
                key={key}
                data-step={index}
                className={cn(
                  'flex flex-col justify-center gap-3 py-8 transition-opacity duration-500 lg:min-h-[64vh]',
                  index > active && 'lg:opacity-30'
                )}
              >
                <p
                  aria-hidden
                  className={cn(
                    'heading-3 tabular transition-colors',
                    index === active ? 'text-primary-hover' : 'text-muted'
                  )}
                >
                  {index + 1}
                </p>
                <h3 className="heading-5 md:heading-4">{t(`home.steps.${key}.title`)}</h3>
                <p className="body-7 max-w-[46ch]">{t(`home.steps.${key}.body`)}</p>
                <ProductStage step={stage} compact className="mt-3 lg:hidden" />
              </li>
            ))}
          </ol>
        </div>

        <div className="relative hidden lg:block">
          <div className="sticky top-[var(--header-height)] flex h-[calc(100dvh-var(--header-height))] items-center py-8">
            <ProductStage step={STEPS[active].stage} scrolling className="max-h-full w-full" />
          </div>
        </div>
      </div>
    </section>
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
          <span className="heading-6 block">{doctor.full_name}</span>
          <span className="block text-muted">{doctor.specialties.map((item) => item.name).join(', ')}</span>
        </span>
        <span className="text-muted">{[doctor.clinic_name, doctor.city].filter(Boolean).join(', ')}</span>
        <span className="tabular">{soonest ? formatDateTime(soonest, i18n.language) : t('home.indexNoTime')}</span>
        <span className="heading-6 tabular md:text-right">{formatCurrency(doctor.consultation_fee, i18n.language)}</span>
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
      <Reveal className="home-gutter">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <h2 id="index-title" className="heading-4 md:heading-3">
              {t('home.indexTitle')}
            </h2>
            <p className="body-7 mt-3 max-w-[56ch] text-muted">{t('home.indexLead')}</p>
          </div>
          {data && (
            <dl className="flex gap-8">
              {counts.map(([count, label]) => (
                <div key={label}>
                  <dd className="heading-4 tabular">{formatNumber(count, i18n.language)}</dd>
                  <dt className="body-6 text-muted">{t(label, { count })}</dt>
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

        <div className="mt-6 rounded-xl border border-border px-3">
          {isPending && <Skeleton className="my-4 h-64 w-full" />}
          {isError && <p className="py-6">{t('home.indexUnavailable')}</p>}
          {data && doctors.length === 0 && <p className="py-6">{t('home.indexEmpty')}</p>}
          <ul data-ui className="[&>li:last-child]:border-b-0">
            {shown.map((doctor, index) => (
              <IndexRow key={doctor.id} doctor={doctor} soonest={nextOpenSlot(slots[index]?.data)?.start_time} />
            ))}
          </ul>
        </div>

        <Button asChild variant="secondary" size="lg" className="mt-8">
          <Link to="/doctors">{t('home.indexMore')}</Link>
        </Button>
      </Reveal>
    </section>
  )
}

function Checks() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="checks-title" className="bg-surface pb-16 md:pb-24">
      <Reveal className="home-gutter">
        <h2 id="checks-title" className="heading-4 md:heading-3">
          {t('home.checksTitle')}
        </h2>
        <dl className="mt-8 grid gap-8 md:grid-cols-3 md:gap-12">
          {CHECKS.map((check) => (
            <div key={check}>
              <dt className="heading-6">{t(`home.checks.${check}.title`)}</dt>
              <dd className="body-3 mt-2 text-muted">{t(`home.checks.${check}.body`)}</dd>
            </div>
          ))}
        </dl>
      </Reveal>
    </section>
  )
}

function Questions() {
  const { t } = useTranslation()
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: QUESTIONS.map((question) => ({
      '@type': 'Question',
      name: t(`home.questions.${question}.q`),
      acceptedAnswer: {
        '@type': 'Answer',
        text: t(`home.questions.${question}.a`, { number: EMERGENCY_NUMBER }),
      },
    })),
  }
  return (
    <section aria-labelledby="questions-title" className="py-16 md:py-24">
      <script type="application/ld+json">{JSON.stringify(schema)}</script>
      <Reveal className="home-gutter">
        <h2 id="questions-title" className="heading-4 md:heading-3">
          {t('home.questionsTitle')}
        </h2>
        <dl className="mt-8 grid gap-x-12 gap-y-8 md:grid-cols-2">
          {QUESTIONS.map((question) => (
            <div key={question}>
              <dt className="heading-6">{t(`home.questions.${question}.q`)}</dt>
              <dd className="body-3 mt-2 text-muted">
                {t(`home.questions.${question}.a`, { number: EMERGENCY_NUMBER })}
              </dd>
            </div>
          ))}
        </dl>
      </Reveal>
    </section>
  )
}

function Promises() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="promises-title" className="bg-surface py-16 md:py-24">
      <Reveal className="home-gutter grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <h2 id="promises-title" className="heading-4 md:heading-3">
          {t('home.promisesTitle')}
        </h2>
        <dl className="flex flex-col gap-6">
          {PROMISES.map((promise) => (
            <div key={promise}>
              <dt className="heading-6">{t(`home.promises.${promise}.title`)}</dt>
              <dd className="body-3 mt-1 text-muted">{t(`home.promises.${promise}.body`)}</dd>
            </div>
          ))}
        </dl>
      </Reveal>
    </section>
  )
}

function Closing() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="start-title" className="bg-primary-tint py-16 md:py-24">
      <Reveal className="home-gutter grid gap-8 lg:grid-cols-2 lg:items-center lg:gap-16">
        <div>
          <h2 id="start-title" className="heading-3 md:heading-2">
            {t('home.startTitle')}
          </h2>
          <p className="body-7 mt-3 max-w-[46ch]">{t('home.startLead')}</p>
        </div>
        <Composer id="closing-input" />
      </Reveal>
    </section>
  )
}

export default function HomePage() {
  return (
    <>
      <Hero />
      <Problem />
      <Benefits />
      <Tagline />
      <HowItWorks />
      <DoctorIndex />
      <Checks />
      <Questions />
      <Promises />
      <Closing />
    </>
  )
}
