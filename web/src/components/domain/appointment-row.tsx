import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
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
}

export function AppointmentRow({ appointment, title, detail, actions }: AppointmentRowProps) {
  const { t, i18n } = useTranslation()
  const { start_time: start } = appointment
  return (
    <li className="slip-stub grid grid-cols-[var(--tear)_minmax(0,1fr)] bg-surface">
      <div className="on-navy flex flex-col justify-center bg-navy p-3 tabular md:p-5">
        <p className="text-lg font-semibold md:text-xl">
          {start ? formatTime(start, i18n.language) : t('appointments.noTime')}
        </p>
        {start && <p className="text-sm text-muted">{formatDate(start, i18n.language)}</p>}
      </div>
      <div className="flex min-w-0 flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between md:p-5">
        <div className="min-w-0">
          <p className="text-lg font-semibold">{title}</p>
          <p className="text-sm text-muted">{detail}</p>
          <Badge tone={STATUS_TONE[appointment.status]} className="mt-1">
            {t(`appointments.status.${appointment.status}`)}
          </Badge>
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </li>
  )
}
