import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'

export default function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <div className="page-gutter py-16">
      <h1 className="font-serif text-2xl">{t('notFound.title')}</h1>
      <p className="prose-width mt-2 text-muted">{t('notFound.body')}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        <Button asChild>
          <Link to="/">{t('notFound.home')}</Link>
        </Button>
        <Button asChild variant="secondary">
          <Link to="/doctors">{t('nav.findDoctors')}</Link>
        </Button>
      </div>
    </div>
  )
}
