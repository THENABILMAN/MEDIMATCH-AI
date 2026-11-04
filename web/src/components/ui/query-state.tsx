import { useTranslation } from 'react-i18next'
import { Button } from './button'
import { EmptyState } from './empty-state'

interface ErrorStateProps {
  error: unknown
  onRetry: () => void
}

function isOffline(error: unknown): boolean {
  return error instanceof Error && error.name === 'NetworkError'
}

/** The error state every data view uses: what happened, then how to retry. */
export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const { t } = useTranslation()
  const offline = isOffline(error)
  return (
    <EmptyState
      title={offline ? t('errors.offlineTitle') : t('errors.loadTitle')}
      description={offline ? t('errors.offlineBody') : t('errors.loadBody')}
      action={
        <Button variant="secondary" onClick={onRetry}>
          {t('common.tryAgain')}
        </Button>
      }
    />
  )
}
