import { Languages } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { LANGUAGE_KEY } from '../../lib/i18n'
import { Button } from '../ui/button'

export function LanguageSwitch({ className }: { className?: string }) {
  const { t, i18n } = useTranslation()
  const next = i18n.language === 'bn' ? 'en' : 'bn'

  function change() {
    void i18n.changeLanguage(next)
    try {
      localStorage.setItem(LANGUAGE_KEY, next)
    } catch {
      // The choice lasts for this visit when storage is blocked
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={change} lang={next} className={className}>
      <Languages aria-hidden className="size-4" strokeWidth={1.75} />
      {t('nav.language')}
    </Button>
  )
}
