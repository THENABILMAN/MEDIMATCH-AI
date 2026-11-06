import { CalendarCheck } from '@phosphor-icons/react'
import { useTranslation } from 'react-i18next'
import { useDoctorSearch, useDoctorsSlots } from '../../api/hooks'
import { nextOpenSlot } from '../../lib/slots'
import { cn } from '../../lib/cn'
import { formatCurrency, formatDateTime, formatNumber } from '../../lib/format'
import { Avatar } from '../ui/avatar'
import { Badge } from '../ui/badge'

const STEPS = [1, 2, 3]
const CANDIDATES = 6
const SHORTLIST_STEP_MS = 120

function PatientLine({ text }: { text: string }) {
  return <p className="rise-in ml-auto max-w-[85%] rounded-xl bg-canvas px-4 py-3">{text}</p>
}

function AssistantLine({ text }: { text: string }) {
  const { t } = useTranslation()
  return (
    <div className="rise-in rounded-xl bg-ai-tint px-4 py-3">
      <p className="caption-4 text-ai">{t('chat.aiLabel')}</p>
      <p className="mt-1">{text}</p>
    </div>
  )
}

function Shortlist() {
  const { t, i18n } = useTranslation()
  const { data } = useDoctorSearch({ page_size: 50 })
  const doctors = data?.items.slice(0, CANDIDATES) ?? []
  const slots = useDoctorsSlots(doctors.map((doctor) => doctor.id))
  // Doctors with a time to book come first, as they do in the real shortlist
  const ranked = doctors
    .map((doctor, position) => ({ doctor, soonest: nextOpenSlot(slots[position]?.data) }))
    .sort((a, b) => Number(Boolean(b.soonest)) - Number(Boolean(a.soonest)))
    .slice(0, 3)
  return (
    <ol className="rise-in rounded-xl border border-border">
      {ranked.map(({ doctor, soonest }, index) => {
        return (
          <li
            key={doctor.id}
            style={{ animationDelay: `${index * SHORTLIST_STEP_MS}ms` }}
            className="flex animate-link-in items-start gap-3 border-b border-border p-3 last:border-b-0"
          >
            <span className="heading-5 text-muted tabular">{formatNumber(index + 1, i18n.language)}</span>
            <div className="min-w-0 flex-1">
              <p className="body-1">{doctor.full_name}</p>
              <p className="body-6 text-muted">{doctor.specialties[0]?.name}</p>
              <p className="body-6 tabular">
                {soonest ? formatDateTime(soonest.start_time, i18n.language) : t('home.indexNoTime')}
                {' · '}
                {formatCurrency(doctor.consultation_fee, i18n.language)}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function Booked() {
  const { t, i18n } = useTranslation()
  const { data } = useDoctorSearch({ page_size: 50 })
  const doctors = data?.items.slice(0, CANDIDATES) ?? []
  const slots = useDoctorsSlots(doctors.map((doctor) => doctor.id))
  const index = Math.max(
    slots.findIndex((query) => nextOpenSlot(query.data)),
    0
  )
  const doctor = doctors[index]
  const slot = nextOpenSlot(slots[index]?.data)
  if (!doctor || !slot) return null
  return (
    <div className="rise-in rounded-xl bg-primary-tint p-4">
      <p className="flex items-center gap-2 body-5 text-primary-hover">
        <CalendarCheck aria-hidden className="size-4" />
        {t('home.previewBooked')}
      </p>
      <p className="mt-2 heading-4 tabular">{formatDateTime(slot.start_time, i18n.language)}</p>
      <div className="mt-3 flex items-center gap-3">
        <Avatar name={doctor.full_name ?? ''} />
        <div className="min-w-0">
          <p className="body-1">{doctor.full_name}</p>
          <Badge tone="success">{t('verification.status.approved')}</Badge>
        </div>
      </div>
    </div>
  )
}

/** The chat, played one step at a time. It only shows: no field or button here can be pressed. */
export function ProductStage({
  step,
  compact,
  scrolling,
  className,
}: {
  step: number
  compact?: boolean
  scrolling?: boolean
  className?: string
}) {
  const { t } = useTranslation()
  // On a phone each step shows only its own moment, so the story stays short
  const past = (from: number) => step >= from && !(compact && step > 1)
  return (
    <figure
      data-ui
      aria-label={t('home.exampleLabel')}
      className={cn('m-0 flex flex-col overflow-hidden rounded-xl border border-border bg-surface', className)}
    >
      <figcaption className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <span className="title-2">{t('chat.title')}</span>
        <Badge tone="ai">{t(scrolling ? 'home.exampleScroll' : 'home.exampleTag')}</Badge>
      </figcaption>
      <div inert className="flex flex-1 flex-col justify-end gap-3 p-4">
        {!compact && <AssistantLine text={t('home.previewGreeting')} />}
        {past(0) && <PatientLine text={t('home.previewPatient')} />}
        {past(1) && <AssistantLine text={t('home.previewAssistant')} />}
        {step >= 2 && !compact && <PatientLine text={t('chat.suggest.fewDays')} />}
        {step === 2 && <AssistantLine text={t('home.previewShortlist')} />}
        {step === 2 && <Shortlist />}
        {step === 3 && <Booked />}
      </div>
      <div aria-hidden className="flex gap-1 px-4">
        {scrolling &&
          STEPS.map((item, index) => (
            <span key={item} className="h-1 flex-1 overflow-hidden rounded-full bg-border">
              <span
                data-stage-bar
                style={{ transform: `scaleX(clamp(0, calc(var(--how, 0) * ${STEPS.length} - ${index}), 1))` }}
                className="block h-full origin-left bg-primary"
              />
            </span>
          ))}
      </div>
      <p className="px-4 py-3 body-6 text-ai">{t('chat.disclaimer')}</p>
    </figure>
  )
}
