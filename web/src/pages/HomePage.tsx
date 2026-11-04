import { ArrowRight, ChevronDown, Phone } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useDoctorSearch } from '../api/hooks'
import { DoctorSlip } from '../components/domain/doctor-card'
import { SerialFinder } from '../components/domain/serial-finder'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { EMERGENCY_NUMBER } from '../lib/constants'
import { formatNumber } from '../lib/format'
import credits from '../locales/image-credits.json'

const CHECKS = [
  ['license', 'BMDC'],
  ['review', 'Approved'],
  ['recheck', 'Reviewed'],
] as const
const QUESTIONS = ['diagnose', 'emergency', 'language', 'privacy', 'fee', 'cancel', 'join'] as const
const FOOTER_LINKS = [
  ['/doctors', 'nav.findDoctors'],
  ['/chat', 'nav.assistant'],
  ['/register?role=doctor', 'home.forDoctors'],
] as const

function Hero() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="home-title" className="overflow-hidden pt-4 pb-8 pl-4 md:pt-8 md:pb-12 md:pl-8">
      <div className="hero-slip slip bg-navy lg:grid lg:min-h-[calc(100dvh-var(--header-height)-5rem)] lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="on-navy rise-in flex flex-col justify-center gap-6 py-10 pr-4 pl-6 md:py-16 md:pr-10 md:pl-14">
          <h1 id="home-title" className="display">
            {t('home.title')}
          </h1>
          <p className="max-w-[46ch] text-lg">{t('home.lead')}</p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link to="/chat">
                {t('home.startChat')}
                <ArrowRight aria-hidden className="size-5" strokeWidth={2} />
              </Link>
            </Button>
            <Button asChild variant="secondary" size="lg">
              <Link to="/doctors">{t('home.browse')}</Link>
            </Button>
          </div>
          <p className="max-w-[52ch] text-sm text-muted">{t('home.emergency', { number: EMERGENCY_NUMBER })}</p>
        </div>

        <figure className="relative m-0 grid min-w-0 content-center overflow-hidden p-4 pt-0 md:p-8 lg:p-12">
          <img
            src="/images/dmc-1940s.webp"
            alt={t('home.images.dmc')}
            width={1600}
            height={1089}
            className="absolute inset-0 hidden size-full object-cover lg:block"
          />
          <div className="rise-in relative mx-auto w-full max-w-md [--delay:160ms]">
            <SerialFinder />
          </div>
        </figure>
      </div>
    </section>
  )
}

function HowItWorks() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="how-title" className="home-gutter py-14 md:py-24">
      <h2 id="how-title" className="display-2 max-w-[18ch]">
        {t('home.howTitle')}
      </h2>
      <ol className="mt-10 grid items-end gap-4 lg:grid-cols-3">
        <li className="reveal flex flex-col rounded-md bg-sand p-6 lg:min-h-[340px]">
          <p className="rounded-md bg-surface px-4 py-3 text-lg">{t('home.previewPatient')}</p>
          <h3 className="mt-auto pt-8 text-xl font-semibold">{t('home.steps.describe.title')}</h3>
          <p className="mt-2">{t('home.steps.describe.body')}</p>
        </li>
        <li className="reveal on-navy flex flex-col rounded-md bg-navy-raised p-6 lg:min-h-[460px]">
          <div className="rounded-md bg-navy px-4 py-3">
            <p className="text-sm font-medium text-muted">{t('chat.aiLabel')}</p>
            <p className="mt-1 text-lg">{t('home.previewAssistant')}</p>
          </div>
          <div aria-hidden className="mt-3 flex flex-wrap gap-2">
            {(['chat.suggest.today', 'chat.suggest.fewDays', 'chat.suggest.week'] as const).map((key) => (
              <span key={key} className="rounded-sm border border-control px-3 py-1 text-sm">
                {t(key)}
              </span>
            ))}
          </div>
          <h3 className="mt-auto pt-8 text-xl font-semibold">{t('home.steps.clarify.title')}</h3>
          <p className="mt-2">{t('home.steps.clarify.body')}</p>
        </li>
        <li className="reveal on-navy flex flex-col overflow-hidden rounded-md bg-navy lg:min-h-[580px]">
          <img
            src="/images/rickshaws.webp"
            alt={t('home.images.rickshaws')}
            loading="lazy"
            width={1600}
            height={1067}
            className="shutter aspect-[4/3] w-full flex-1 object-cover"
          />
          <div className="p-6">
            <h3 className="text-xl font-semibold">{t('home.steps.choose.title')}</h3>
            <p className="mt-2">{t('home.steps.choose.body')}</p>
          </div>
        </li>
      </ol>
    </section>
  )
}

function Doctors() {
  const { t } = useTranslation()
  const { data, isPending } = useDoctorSearch({ page_size: 50 })
  const doctors = data?.items.slice(0, 3) ?? []
  return (
    <section aria-labelledby="doctors-title" className="overflow-hidden bg-sand py-14 md:py-24">
      <div className="home-gutter grid items-center gap-10 lg:grid-cols-2">
        <div className="relative order-2 mx-auto aspect-square w-full max-w-[640px] lg:order-1">
          <img
            src="/images/ahsan-manzil.webp"
            alt={t('home.images.ahsan')}
            loading="lazy"
            width={1600}
            height={1067}
            className="shutter size-full rounded-full object-cover"
          />
        </div>
        <div className="order-1 lg:order-2">
          <h2 id="doctors-title" className="display-2">
            {t('home.doctorsTitle')}
          </h2>
          <p className="mt-4 max-w-[52ch] text-lg">{t('home.doctorsLead')}</p>
          <ul className="mt-8 flex flex-col gap-3">
            {isPending && [0, 1, 2].map((key) => <Skeleton key={key} className="h-28 w-full" />)}
            {doctors.map((doctor) => (
              <li key={doctor.id} className="reveal">
                <DoctorSlip doctor={doctor} />
              </li>
            ))}
          </ul>
          <Button asChild variant="secondary" className="mt-6">
            <Link to="/doctors">{t('home.doctorsAll')}</Link>
          </Button>
        </div>
      </div>
    </section>
  )
}

function Checks() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="checks-title" className="on-navy bg-navy py-14 md:py-24">
      <div className="home-gutter">
        <h2 id="checks-title" className="display-2 max-w-[18ch]">
          {t('home.checksTitle')}
        </h2>
        <ul className="mt-10 grid gap-4 md:grid-cols-3">
          {CHECKS.map(([check, mark]) => (
            <li key={check} className="reveal slip bg-navy-raised p-6 md:p-8">
              <p aria-hidden className="mark" translate="no">
                {mark}
              </p>
              <h3 className="mt-10 text-xl font-semibold">{t(`home.checks.${check}.title`)}</h3>
              <p className="mt-2">{t(`home.checks.${check}.body`)}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

function tally(names: string[]): [string, number][] {
  const counts = new Map<string, number>()
  names.forEach((name) => counts.set(name, (counts.get(name) ?? 0) + 1))
  return [...counts].sort(([a], [b]) => a.localeCompare(b))
}

function BrowseList({ title, param, entries }: { title: string; param: string; entries: [string, number][] }) {
  const { t, i18n } = useTranslation()
  return (
    <div>
      <h3 className="text-xl font-semibold">{title}</h3>
      <ul className="mt-3 flex flex-col gap-2">
        {entries.map(([name, count]) => (
          <li key={name}>
            <Link
              to={`/doctors?${param}=${encodeURIComponent(name)}`}
              className="group flex min-h-14 items-center justify-between gap-3 rounded-md bg-sand px-4 py-2 transition-colors hover:bg-border"
            >
              <span className="text-lg font-medium">{name}</span>
              <span className="flex shrink-0 items-center gap-2 text-sm">
                {t('home.doctorCount', { count, shown: formatNumber(count, i18n.language) })}
                <ArrowRight
                  aria-hidden
                  className="size-4 transition-transform group-hover:translate-x-1"
                  strokeWidth={2}
                />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Browse() {
  const { t } = useTranslation()
  const { data, isPending } = useDoctorSearch({ page_size: 50 })
  const doctors = data?.items ?? []
  return (
    <section aria-labelledby="browse-title" className="home-gutter grid gap-10 py-14 md:py-24 lg:grid-cols-[5fr_7fr]">
      <div className="order-2 lg:order-1">
        <img
          src="/images/buriganga.webp"
          alt={t('home.images.buriganga')}
          loading="lazy"
          width={1600}
          height={1067}
          className="shutter h-full max-h-[620px] min-h-[280px] w-full rounded-md object-cover"
        />
      </div>
      <div className="order-1 lg:order-2">
        <h2 id="browse-title" className="display-2">
          {t('home.browseTitle')}
        </h2>
        <p className="mt-4 max-w-[52ch] text-lg">{t('home.browseLead')}</p>
        {isPending && <Skeleton className="mt-8 h-56 w-full" />}
        {doctors.length > 0 && (
          <div className="mt-8 grid gap-8 md:grid-cols-2">
            <BrowseList
              title={t('home.bySpecialty')}
              param="specialty"
              entries={tally(doctors.flatMap((doctor) => doctor.specialties.map((item) => item.name)))}
            />
            <BrowseList
              title={t('home.byCity')}
              param="city"
              entries={tally(doctors.flatMap((doctor) => (doctor.city ? [doctor.city] : [])))}
            />
          </div>
        )}
      </div>
    </section>
  )
}

function Questions() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="questions-title" className="home-gutter grid gap-8 pb-14 md:pb-24 lg:grid-cols-[5fr_7fr]">
      <h2 id="questions-title" className="display-2">
        {t('home.questionsTitle')}
      </h2>
      <div className="flex flex-col gap-2">
        {QUESTIONS.map((question) => (
          <details key={question} className="group rounded-md bg-sand">
            <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 px-5 py-3 text-lg font-medium">
              {t(`home.questions.${question}.q`)}
              <ChevronDown
                aria-hidden
                className="size-5 shrink-0 transition-transform group-open:rotate-180"
                strokeWidth={2}
              />
            </summary>
            <p className="max-w-[60ch] px-5 pb-5">{t(`home.questions.${question}.a`, { number: EMERGENCY_NUMBER })}</p>
          </details>
        ))}
      </div>
    </section>
  )
}

function FinalCall() {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="start-title" className="overflow-hidden pr-4 pb-14 md:pr-8 md:pb-24">
      <div className="reveal slip on-navy flex flex-col items-start gap-6 bg-navy py-12 pr-6 pl-4 md:flex-row md:items-center md:justify-between md:py-20 md:pr-14 md:pl-8">
        <div>
          <h2 id="start-title" className="display-2 max-w-[16ch]">
            {t('home.startTitle')}
          </h2>
          <p className="mt-4 max-w-[46ch] text-lg">{t('home.startLead')}</p>
        </div>
        <Button asChild size="lg" className="shrink-0">
          <Link to="/chat">
            {t('home.startChat')}
            <ArrowRight aria-hidden className="size-5" strokeWidth={2} />
          </Link>
        </Button>
      </div>
    </section>
  )
}

function Footer() {
  const { t } = useTranslation()
  return (
    <footer className="on-navy overflow-hidden bg-navy">
      <div className="home-gutter grid gap-8 pt-12 pb-8 md:grid-cols-[2fr_1fr_2fr]">
        <div>
          <p className="max-w-[44ch]">{t('home.footer')}</p>
          <a
            href={`tel:${EMERGENCY_NUMBER}`}
            className="mt-4 inline-flex min-h-11 items-center gap-2 font-semibold underline underline-offset-4"
          >
            <Phone aria-hidden className="size-4" strokeWidth={2} />
            {t('nav.emergency', { number: EMERGENCY_NUMBER })}
          </a>
        </div>
        <ul className="flex flex-col">
          {FOOTER_LINKS.map(([to, label]) => (
            <li key={to}>
              <Link to={to} className="inline-flex min-h-11 items-center underline-offset-4 hover:underline">
                {t(label)}
              </Link>
            </li>
          ))}
        </ul>
        <div>
          <p className="text-sm font-semibold">{t('home.creditsTitle')}</p>
          <ul className="mt-1 text-sm text-muted">
            {credits.map((credit) => (
              <li key={credit.page}>
                <a href={credit.page} rel="noreferrer" target="_blank" className="underline underline-offset-2">
                  {credit.title}
                </a>
                {`, ${credit.creator}, ${credit.license}`}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <p aria-hidden className="wordmark" translate="no">
        MediMatch
      </p>
    </footer>
  )
}

export default function HomePage() {
  return (
    <>
      <Hero />
      <HowItWorks />
      <Doctors />
      <Checks />
      <Browse />
      <Questions />
      <FinalCall />
      <Footer />
    </>
  )
}
