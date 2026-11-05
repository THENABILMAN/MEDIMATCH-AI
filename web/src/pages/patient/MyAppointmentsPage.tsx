import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useAppointments, useCancelAppointment } from '../../api/hooks'
import { AppointmentPanel, appointmentTab, AppointmentsSkeleton, type AppointmentTab } from '../../components/domain/appointment-list'
import { AppointmentRow } from '../../components/domain/appointment-row'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { ConfirmDialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { Field } from '../../components/ui/field'
import { Textarea } from '../../components/ui/input'
import { ErrorState } from '../../components/ui/query-state'
import { Tabs } from '../../components/ui/tabs'
import { useToast } from '../../components/ui/toast'
import { errorMessage } from '../../lib/errors'
import { formatDateTime } from '../../lib/format'
import { useUrlState } from '../../lib/url-state'
import type { Appointment } from '../../types'

const TABS: AppointmentTab[] = ['upcoming', 'past', 'cancelled']

export default function MyAppointmentsPage() {
  const { t, i18n } = useTranslation()
  const { toast } = useToast()
  const { params, set } = useUrlState()
  const appointments = useAppointments()
  const cancel = useCancelAppointment()
  const [cancelling, setCancelling] = useState<Appointment | null>(null)
  const [reason, setReason] = useState('')
  const [now] = useState(() => Date.now())

  const tab = (TABS as string[]).includes(params.get('tab') ?? '') ? (params.get('tab') as AppointmentTab) : 'upcoming'
  const visible = useMemo(
    () => (appointments.data ?? []).filter((item) => appointmentTab(item, now) === tab),
    [appointments.data, now, tab]
  )

  async function confirmCancel() {
    if (!cancelling) return
    try {
      await cancel.mutateAsync({ id: cancelling.id, reason })
      toast(t('appointments.cancelled'))
      setCancelling(null)
      setReason('')
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader title={t('appointments.title')} />
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
            title={t(`appointments.empty.${tab}.title`)}
            description={t(`appointments.empty.${tab}.body`)}
            action={
              tab === 'upcoming' ? (
                <Button asChild>
                  <Link to="/chat">{t('home.startChat')}</Link>
                </Button>
              ) : undefined
            }
          />
        ) : (
          <AppointmentPanel>
            {visible.map((appointment, index) => (
              <AppointmentRow
                key={appointment.id}
                featured={tab === 'upcoming' && index === 0}
                appointment={appointment}
                title={appointment.doctor?.full_name ?? t('appointments.unknownDoctor')}
                detail={[appointment.doctor?.specialties.join(', '), appointment.doctor?.clinic_name, appointment.doctor?.city]
                  .filter(Boolean)
                  .join(' · ')}
                actions={
                  tab === 'upcoming' ? (
                    <Button variant="secondary" size="sm" onClick={() => setCancelling(appointment)}>
                      {t('appointments.cancel')}
                    </Button>
                  ) : undefined
                }
              />
            ))}
          </AppointmentPanel>
        )}
      </Tabs>

      <ConfirmDialog
        open={Boolean(cancelling)}
        onOpenChange={(open) => !open && setCancelling(null)}
        title={t('appointments.cancelTitle')}
        description={t('appointments.cancelBody', {
          doctor: cancelling?.doctor?.full_name ?? '',
          time: cancelling?.start_time ? formatDateTime(cancelling.start_time, i18n.language) : '',
        })}
        confirmLabel={t('appointments.cancel')}
        cancelLabel={t('appointments.keep')}
        loading={cancel.isPending}
        onConfirm={() => void confirmCancel()}
      >
        <Field label={t('appointments.cancelReason')} optional={t('common.optional')}>
          {(control) => (
            <Textarea {...control} value={reason} maxLength={300} onChange={(event) => setReason(event.target.value)} />
          )}
        </Field>
      </ConfirmDialog>
    </div>
  )
}
