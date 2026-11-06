import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { usePricing } from '../api/hooks'
import { Button } from '../components/ui/button'
import { formatCurrency } from '../lib/format'

const STEPS = ['profile', 'review', 'plan'] as const

function Price({ amount, unit }: { amount: number | null | undefined; unit: string }) {
  const { t, i18n } = useTranslation()
  if (!amount) return <p className="body-6 mt-3 text-muted">{t('billing.priceLater')}</p>
  return (
    <p className="heading-5 mt-3 tabular">
      {formatCurrency(amount, i18n.language)} <span className="body-6 text-muted">{unit}</span>
    </p>
  )
}

export default function ForDoctorsPage() {
  const { t } = useTranslation()
  // Prices are extra detail here, so the page still reads well if they fail to load
  const { data: pricing } = usePricing()
  return (
    <div className="page-gutter py-8 md:py-16">
      <title>{`${t('forDoctors.title')} | MediMatch AI`}</title>
      <div className="max-w-[680px]">
        <h1 className="heading-3 md:heading-2">{t('forDoctors.title')}</h1>
        <p className="body-7 mt-4">{t('forDoctors.lead')}</p>
        <Button asChild size="lg" className="mt-6">
          <Link to="/register?role=doctor">{t('forDoctors.action')}</Link>
        </Button>
      </div>

      <section aria-labelledby="plans-title" className="mt-16">
        <h2 id="plans-title" className="heading-4">
          {t('forDoctors.plansTitle')}
        </h2>
        <p className="body-3 mt-2 text-muted">{t('forDoctors.plansLead')}</p>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="heading-6">{t('billing.plan.booking_fee.title')}</h3>
            <p className="body-3 mt-2 text-muted">{t('billing.plan.booking_fee.body')}</p>
            <Price amount={pricing?.booking_fee_bdt} unit={t('billing.perAppointment')} />
          </article>
          <article className="rounded-xl border border-border bg-surface p-6">
            <h3 className="heading-6">{t('billing.plan.subscription.title')}</h3>
            <p className="body-3 mt-2 text-muted">{t('billing.plan.subscription.body')}</p>
            <Price amount={pricing?.subscription_monthly_bdt} unit={t('billing.perMonth')} />
          </article>
        </div>
      </section>

      <section aria-labelledby="join-title" className="mt-16">
        <h2 id="join-title" className="heading-4">
          {t('forDoctors.joinTitle')}
        </h2>
        <ol className="mt-6 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step}>
              <p aria-hidden className="heading-5 tabular text-muted">
                {index + 1}
              </p>
              <h3 className="heading-6 mt-1">{t(`forDoctors.steps.${step}.title`)}</h3>
              <p className="body-3 mt-1 text-muted">{t(`forDoctors.steps.${step}.body`)}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
