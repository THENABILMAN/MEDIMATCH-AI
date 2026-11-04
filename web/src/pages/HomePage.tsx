import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { LogoMark } from '../components/layout/logo'
import { Button } from '../components/ui/button'
import { EMERGENCY_NUMBER } from '../lib/constants'

const STEPS = ['describe', 'clarify', 'choose'] as const
const CHECKS = ['license', 'review', 'recheck'] as const

function ConversationPreview() {
  const { t } = useTranslation()
  return (
    <figure className="rounded-md border border-border bg-surface p-4 md:p-6">
      <figcaption className="text-sm text-muted">{t('home.previewCaption')}</figcaption>
      <div className="mt-4 flex flex-col gap-4" aria-hidden>
        <p className="ml-auto max-w-[85%] rounded-md border border-border px-4 py-3">{t('home.previewPatient')}</p>
        <div className="border-l-2 border-ai pl-4">
          <p className="text-xs font-medium text-ai">{t('chat.aiLabel')}</p>
          <p className="mt-1">{t('home.previewAssistant')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(['chat.suggest.today', 'chat.suggest.fewDays', 'chat.suggest.week'] as const).map((key) => (
            <span key={key} className="rounded-sm border border-control px-3 py-1 text-sm">
              {t(key)}
            </span>
          ))}
        </div>
      </div>
    </figure>
  )
}

export default function HomePage() {
  const { t } = useTranslation()
  return (
    <>
      <section className="border-b border-border bg-surface">
        <div className="page-gutter grid gap-10 py-12 md:py-16 lg:grid-cols-12 lg:gap-6 lg:py-20">
          <div className="lg:col-span-7">
            <h1 className="max-w-[16ch] font-serif text-2xl md:text-3xl">{t('home.title')}</h1>
            <p className="prose-width mt-4 text-lg text-muted">{t('home.lead')}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild>
                <Link to="/chat">{t('home.startChat')}</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link to="/doctors">{t('home.browse')}</Link>
              </Button>
            </div>
            <p className="prose-width mt-6 text-sm text-muted">
              {t('home.emergency', { number: EMERGENCY_NUMBER })}
            </p>
          </div>
          <div className="lg:col-span-5">
            <ConversationPreview />
          </div>
        </div>
      </section>

      <section aria-labelledby="how-title" className="page-gutter grid gap-6 py-12 md:py-16 lg:grid-cols-12">
        <h2 id="how-title" className="font-serif text-xl lg:col-span-4">
          {t('home.howTitle')}
        </h2>
        <ol className="border-t border-border lg:col-span-8">
          {STEPS.map((step, index) => (
            <li key={step} className="grid grid-cols-[32px_1fr] gap-x-3 border-b border-border py-4">
              <span aria-hidden className="font-serif text-lg text-muted tabular">
                {index + 1}
              </span>
              <div>
                <h3 className="font-semibold">{t(`home.steps.${step}.title`)}</h3>
                <p className="prose-width text-muted">{t(`home.steps.${step}.body`)}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="checks-title" className="border-t border-border bg-surface">
        <div className="page-gutter grid gap-6 py-12 md:py-16 lg:grid-cols-12">
          <h2 id="checks-title" className="font-serif text-xl lg:col-span-4">
            {t('home.checksTitle')}
          </h2>
          <dl className="lg:col-span-8">
            {CHECKS.map((check) => (
              <div key={check} className="border-b border-border py-4 first:pt-0 last:border-b-0">
                <dt className="font-semibold">{t(`home.checks.${check}.title`)}</dt>
                <dd className="prose-width text-muted">{t(`home.checks.${check}.body`)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="page-gutter flex flex-col gap-3 py-6 text-sm text-muted md:flex-row md:items-center md:justify-between">
          <p className="flex items-center gap-2" translate="no">
            <LogoMark className="size-5" />
            MediMatch
          </p>
          <p className="prose-width">{t('home.footer')}</p>
          <Link to="/register?role=doctor" className="whitespace-nowrap text-primary underline underline-offset-4">
            {t('home.forDoctors')}
          </Link>
        </div>
      </footer>
    </>
  )
}
