import { useTranslation } from 'react-i18next'

/** Always on the chat screen: short, permanent, never a modal. */
export function AIDisclaimer() {
  const { t } = useTranslation()
  return (
    <p data-testid="ai-disclaimer" className="body-6 text-ai">
      {t('chat.disclaimer')}
    </p>
  )
}
