import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { Appointment } from '../../types'
import { Skeleton } from '../ui/skeleton'

export type AppointmentTab = 'upcoming' | 'past' | 'cancelled'

export function appointmentTab(appointment: Appointment, now: number): AppointmentTab {
  if (appointment.status === 'cancelled') return 'cancelled'
  if (appointment.status === 'completed') return 'past'
  return appointment.start_time && new Date(appointment.start_time).getTime() < now ? 'past' : 'upcoming'
}

export function AppointmentsSkeleton() {
  const { t } = useTranslation()
  return (
    <div role="status" className="rounded-md border border-border bg-surface">
      <span className="sr-only">{t('common.loading')}</span>
      {[0, 1, 2].map((row) => (
        <div key={row} className="flex gap-6 border-b border-border p-4 last:border-b-0 md:p-5">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 flex-1" />
        </div>
      ))}
    </div>
  )
}

export function AppointmentPanel({ children }: { children: ReactNode }) {
  return <ul className="rounded-md border border-border bg-surface">{children}</ul>
}
