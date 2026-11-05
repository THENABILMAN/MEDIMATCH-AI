import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useAppointments, useCancelAppointment, useCompleteAppointment } from '../../api/hooks'
import { AppointmentPanel, appointmentTab, AppointmentsSkeleton, type AppointmentTab } from '../../components/domain/appointment-list'
import { AppointmentRow } from '../../components/domain/appointment-row'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { ConfirmDialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { ErrorState } from '../../components/ui/query-state'
import { Tabs } from '../../components/ui/tabs'
import { useToast } from '../../components/ui/toast'
import { errorMessage } from '../../lib/errors'
import { formatDateTime } from '../../lib/format'
import { useUrlState } from '../../lib/url-state'
import type { Appointment } from '../../types'

const TABS: AppointmentTab[] = ['upcoming', 'past', 'cancelled']

export default function DoctorAppointmentsPage() {
  const { t, i18n } = useTranslation()
  const { toast } = useToast()
  const { params, set } = useUrlState()
  const appointments = useAppointments()
  const cancel = useCancelAppointment()
  const complete = useCompleteAppointment()
  const [cancelling, setCancelling] = useState<Appointment | null>(null)
  const [now] = useState(() => Date.now())

  const tab = (TABS as string[]).includes(params.get('tab') ?? '') ? (params.get('tab') as AppointmentTab) : 'upcoming'
  const visible = useMemo(
    () => (appointments.data ?? []).filter((item) => appointmentTab(item, now) === tab),
    [appointments.data, now, tab]
  )

  async function markComplete(id: string) {
    try {
      await complete.mutateAsync(id)
      toast(t('appointments.completed'))
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  async function confirmCancel() {
    if (!cancelling) return
    try {
      await cancel.mutateAsync({ id: cancelling.id })
      toast(t('appointments.cancelled'))
      setCancelling(null)
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader title={t('appointments.doctorTitle')} />
      <Tabs
        value={tab}
        onValueChange={(next) => set({ tab: next === 'upcoming' ? undefined : next })}
        tabs={TABS.map((item) => ({ value: item, label: t(`appointments.tab.${item}`) }))}
      >
        {appointments.isPending ? (
          <AppointmentsSkeleton />
        ) : appointments.isError ? (
          <ErrorState error={appointments.error} onRetry={() => void appointments.refetch()} />
        ) : visible.length === 0 ? (
          <EmptyState
            illustration="calendar"
            title={t(`appointments.doctorEmpty.${tab}.title`)}
            description={t(`appointments.doctorEmpty.${tab}.body`)}
            action={
              tab === 'upcoming' ? (
                <Button asChild>
                  <Link to="/doctor/availability">{t('verification.setAvailability')}</Link>
                </Button>
              ) : undefined
            }
          />
        ) : (
          <AppointmentPanel>
            {visible.map((appointment, index) => {
              const booked = appointment.status === 'booked'
              return (
                <AppointmentRow
                  key={appointment.id}
                  featured={tab === 'upcoming' && index === 0}
                  appointment={appointment}
                  title={appointment.patient?.full_name ?? t('appointments.unknownPatient')}
                  detail={appointment.patient?.phone ?? t('appointments.noPhone')}
                  actions={
                    booked ? (
                      <>
                        <Button size="sm" loading={complete.isPending} onClick={() => void markComplete(appointment.id)}>
                          {t('appointments.markComplete')}
                        </Button>
                        {tab === 'upcoming' && (
                          <Button variant="secondary" size="sm" onClick={() => setCancelling(appointment)}>
                            {t('appointments.cancel')}
                          </Button>
                        )}
                      </>
                    ) : undefined
                  }
                />
              )
            })}
          </AppointmentPanel>
        )}
      </Tabs>

      <ConfirmDialog
        open={Boolean(cancelling)}
        onOpenChange={(open) => !open && setCancelling(null)}
        title={t('appointments.cancelTitle')}
        description={t('appointments.cancelBodyDoctor', {
          patient: cancelling?.patient?.full_name ?? '',
          time: cancelling?.start_time ? formatDateTime(cancelling.start_time, i18n.language) : '',
        })}
        confirmLabel={t('appointments.cancel')}
        cancelLabel={t('appointments.keep')}
        loading={cancel.isPending}
        onConfirm={() => void confirmCancel()}
      />
    </div>
  )
}
