import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { EMERGENCY_NUMBER } from '../lib/constants'

const SECTIONS = {
  privacy: ['stored', 'providers', 'retention', 'emergency', 'closing'],
  terms: ['service', 'emergency', 'assistant', 'doctors', 'billing', 'appointments', 'account'],
} as const

/** Plain statements of what the product does. A lawyer reviews this wording before launch. */
export default function LegalPage({ page }: { page: keyof typeof SECTIONS }) {
  const { t } = useTranslation()
  return (
    <article className="page-gutter py-8 md:py-16">
      <div className="mx-auto max-w-[680px]">
        <title>{`${t(`legal.${page}.title`)} | MediMatch AI`}</title>
        <h1 className="heading-3">{t(`legal.${page}.title`)}</h1>
        <p className="body-7 mt-3 text-muted">{t(`legal.${page}.lead`)}</p>
        {SECTIONS[page].map((section) => (
          <section key={section} className="mt-8">
            <h2 className="heading-6">{t(`legal.${page}.${section}.title`)}</h2>
            <p className="body-3 mt-2">{t(`legal.${page}.${section}.body`, { number: EMERGENCY_NUMBER })}</p>
          </section>
        ))}
        <Link to="/" className="body-5 mt-8 inline-block underline underline-offset-4">
          {t('legal.home')}
        </Link>
      </div>
    </article>
  )
}
