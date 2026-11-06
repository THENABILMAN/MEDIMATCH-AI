import { Phone } from '@phosphor-icons/react'
import { useTranslation } from 'react-i18next'
import { EMERGENCY_NUMBER } from '../../lib/constants'

/**
 * Shows the backend's self-harm message exactly as received, calmly: no red and no siren, because
 * alarm can make things worse for someone in crisis. Like EmergencyNotice, it has no close control
 * and accepts no recommendations, so nothing can soften, hide or follow it.
 */
export function CrisisNotice({ message }: { message: string }) {
  const { t } = useTranslation()
  return (
    <section
      role="alert"
      data-testid="crisis-notice"
      className="rounded-xl border border-control bg-surface p-4 md:p-6"
    >
      <p className="title-2">{t('chat.crisisHeading')}</p>
      <p className="body-7 mt-3 whitespace-pre-line">{message}</p>
      <a
        href={`tel:${EMERGENCY_NUMBER}`}
        className="title-2 mt-4 flex h-12 items-center justify-center gap-2 rounded-full bg-primary text-white transition-[background-color,transform] hover:bg-primary-hover active:scale-[0.98]"
      >
        <Phone aria-hidden className="size-5" />
        {t('chat.callEmergency', { number: EMERGENCY_NUMBER })}
      </a>
    </section>
  )
}
