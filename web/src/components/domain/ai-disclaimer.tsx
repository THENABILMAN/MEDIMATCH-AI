import { Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'

/** Always on the chat screen: short, permanent, never a modal. */
export function AIDisclaimer() {
  const { t } = useTranslation()
  return (
    <p data-testid="ai-disclaimer" className="flex items-center gap-2 text-sm text-ai">
      <Sparkles aria-hidden className="size-4 shrink-0" strokeWidth={1.75} />
      {t('chat.disclaimer')}
    </p>
  )
}
