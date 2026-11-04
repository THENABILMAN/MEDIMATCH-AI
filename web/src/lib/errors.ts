import type { TFunction } from 'i18next'
import { ApiError, NetworkError } from '../api/client'

/** A message for the person using the app: the API's own wording, or the offline hint. */
export function errorMessage(error: unknown, t: TFunction): string {
  if (error instanceof NetworkError) return t('errors.offlineBody')
  if (error instanceof ApiError && error.status < 500) return error.message
  return t('errors.loadBody')
}
