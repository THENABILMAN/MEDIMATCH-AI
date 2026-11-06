import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/cn'
import { formatDate, formatTime } from '../../lib/format'
import type { Appointment, AppointmentStatus } from '../../types'
import { Badge, type BadgeProps } from '../ui/badge'

const STATUS_TONE: Record<AppointmentStatus, BadgeProps['tone']> = {
  booked: 'primary',
  completed: 'success',
  cancelled: 'neutral',
}

interface AppointmentRowProps {
  appointment: Appointment
  title: string
  detail: string
  actions?: ReactNode
  featured?: boolean
}

export function AppointmentRow({ appointment, title, detail, actions, featured }: AppointmentRowProps) {
  const { t, i18n } = useTranslation()
  const { start_time: start } = appointment
  return (
    <li
      className={cn(
        'grid gap-3 border-b border-border p-4 last:border-b-0 md:grid-cols-[220px_1fr_auto] md:items-center md:p-4',
        featured && 'bg-primary-tint md:py-8'
      )}
    >
      <div className="tabular">
        <p className={cn('', featured ? 'heading-3' : 'heading-5')}>
          {start ? formatTime(start, i18n.language) : t('appointments.noTime')}
        </p>
        {start && <p className="body-6 text-muted">{formatDate(start, i18n.language)}</p>}
      </div>
      <div className="min-w-0">
        <p className={cn('body-1', featured && 'heading-5')}>{title}</p>
        <p className="body-6 text-muted">{detail}</p>
        <Badge tone={STATUS_TONE[appointment.status]} className="mt-1">
          {t(`appointments.status.${appointment.status}`)}
        </Badge>
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </li>
  )
}
