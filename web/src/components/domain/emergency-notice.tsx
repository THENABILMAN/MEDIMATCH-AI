import { Phone, Siren } from '@phosphor-icons/react'
import { useTranslation } from 'react-i18next'
import { EMERGENCY_NUMBER } from '../../lib/constants'

/**
 * Shows the backend's emergency message exactly as received. It has no close control and
 * accepts no recommendations, so nothing can soften, hide or follow it.
 */
export function EmergencyNotice({ message }: { message: string }) {
  const { t } = useTranslation()
  return (
    <section
      role="alert"
      data-testid="emergency-notice"
      className="rounded-xl bg-danger p-4 text-white md:p-6"
    >
      <p className="flex items-center gap-2 title-2">
        <Siren aria-hidden className="size-6 shrink-0" />
        {t('chat.emergencyHeading')}
      </p>
      <p className="mt-3 body-7 whitespace-pre-line">{message}</p>
      <a
        href={`tel:${EMERGENCY_NUMBER}`}
        className="mt-4 flex h-12 items-center justify-center gap-2 rounded-full bg-white title-2 text-danger transition-colors hover:bg-danger-tint focus-visible:outline-white"
      >
        <Phone aria-hidden className="size-5" />
        {t('chat.callEmergency', { number: EMERGENCY_NUMBER })}
      </a>
    </section>
  )
}
