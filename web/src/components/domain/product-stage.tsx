import { useTranslation } from 'react-i18next'
import { useDoctorSearch, useDoctorsSlots } from '../../api/hooks'
import { nextOpenSlot } from '../../lib/slots'
import { cn } from '../../lib/cn'
import { formatCurrency, formatDateTime, formatDayNumber, formatNumber, formatTime, formatWeekday } from '../../lib/format'
import { Avatar } from '../ui/avatar'
import { Badge } from '../ui/badge'

const CHIPS = ['chat.suggest.today', 'chat.suggest.fewDays', 'chat.suggest.week'] as const

function PatientLine({ text }: { text: string }) {
  return <p className="rise-in ml-auto max-w-[85%] rounded-md bg-canvas px-4 py-3">{text}</p>
}

function AssistantLine({ text }: { text: string }) {
  const { t } = useTranslation()
  return (
    <div className="rise-in rounded-md bg-ai-tint px-4 py-3">
      <p className="text-xs font-medium text-ai">{t('chat.aiLabel')}</p>
      <p className="mt-1">{text}</p>
    </div>
  )
}

function Shortlist() {
  const { t, i18n } = useTranslation()
  const { data } = useDoctorSearch({ page_size: 50 })
  const doctors = data?.items.slice(0, 3) ?? []
  const slots = useDoctorsSlots(doctors.map((doctor) => doctor.id))
  return (
    <ol className="rise-in rounded-md border border-border">
      {doctors.map((doctor, index) => {
        const soonest = nextOpenSlot(slots[index]?.data)
        return (
          <li key={doctor.id} className="flex items-start gap-3 border-b border-border p-3 last:border-b-0">
            <span className="font-serif text-xl text-muted tabular">{formatNumber(index + 1, i18n.language)}</span>
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{doctor.full_name}</p>
              <p className="text-sm text-muted">{doctor.specialties[0]?.name}</p>
              <p className="text-sm tabular">
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

function Booking() {
  const { t, i18n } = useTranslation()
  const { data } = useDoctorSearch({ page_size: 50 })
  const doctors = data?.items.slice(0, 3) ?? []
  const slots = useDoctorsSlots(doctors.map((doctor) => doctor.id))
  const index = Math.max(
    slots.findIndex((query) => nextOpenSlot(query.data)),
    0
  )
  const doctor = doctors[index]
  const open = (slots[index]?.data ?? [])
    .filter((slot) => !slot.is_booked && new Date(slot.start_time) > new Date())
    .sort((a, b) => a.start_time.localeCompare(b.start_time))
    .slice(0, 3)
  if (!doctor) return null
  return (
    <div className="rise-in rounded-md border border-border p-4">
      <div className="flex items-center gap-3">
        <Avatar name={doctor.full_name ?? ''} />
        <div className="min-w-0">
          <p className="font-semibold">{doctor.full_name}</p>
          <Badge tone="success">{t('verification.status.approved')}</Badge>
        </div>
      </div>
      <p className="mt-4 text-sm font-medium">{t('home.previewBooked')}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {open.map((slot, position) => (
          <span
            key={slot.id}
            className={cn(
              'rounded-sm border px-3 py-2 text-sm tabular',
              position === 0 ? 'border-primary bg-primary-tint font-medium text-primary-hover' : 'border-control'
            )}
          >
            {formatWeekday(slot.start_time, i18n.language)} {formatDayNumber(slot.start_time, i18n.language)},{' '}
            {formatTime(slot.start_time, i18n.language)}
          </span>
        ))}
      </div>
      <p className="mt-4 flex h-11 items-center justify-center rounded-sm bg-primary font-medium text-white">
        {t('home.previewBook')}
      </p>
    </div>
  )
}

/** The real chat, played one step at a time. It only shows; `inert` keeps it out of the tab order. */
export function ProductStage({ step, compact, className }: { step: number; compact?: boolean; className?: string }) {
  const { t } = useTranslation()
  // On a phone each step shows only its own moment, so the story stays short
  const past = (from: number) => step >= from && !(compact && step > from)
  return (
    <figure
      data-ui
      aria-label={t('home.exampleLabel')}
      className={cn('on-paper m-0 flex flex-col overflow-hidden rounded-md bg-surface', className)}
    >
      <figcaption className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="font-serif text-lg">{t('chat.title')}</span>
        <Badge tone="ai">{t('home.exampleTag')}</Badge>
      </figcaption>
      <div inert className="flex flex-1 flex-col justify-end gap-3 overflow-hidden p-4">
        {!compact && <AssistantLine text={t('home.previewGreeting')} />}
        {past(0) && <PatientLine text={t('home.previewPatient')} />}
        {past(1) && <AssistantLine text={t('home.previewAssistant')} />}
        {step === 1 && (
          <div className="rise-in flex flex-wrap gap-2">
            {CHIPS.map((key) => (
              <span key={key} className="rounded-sm border border-control px-3 py-1 text-sm">
                {t(key)}
              </span>
            ))}
          </div>
        )}
        {step >= 2 && !compact && <PatientLine text={t(CHIPS[1])} />}
        {step === 2 && <AssistantLine text={t('home.previewShortlist')} />}
        {step === 2 && <Shortlist />}
        {step === 3 && <Booking />}
      </div>
      {!compact && (
        <div className="flex gap-2 border-t border-border px-4 pt-3" aria-hidden>
          <span className="flex h-11 flex-1 items-center rounded-sm border border-control px-3 text-muted">
            {t('chat.inputPlaceholder')}
          </span>
          <span className="flex h-11 items-center rounded-sm bg-primary px-4 font-medium text-white">{t('chat.send')}</span>
        </div>
      )}
      <p className="px-4 py-3 text-sm text-ai">{t('chat.disclaimer')}</p>
    </figure>
  )
}
