import { CaretLeft } from '@phosphor-icons/react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../api/client'
import { useBookSlot, useDoctor, useDoctorSlots } from '../../api/hooks'
import { DoctorCardDetailed } from '../../components/domain/doctor-card'
import { SlotPicker } from '../../components/domain/slot-picker'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { ConfirmDialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'
import { useToast } from '../../components/ui/toast'
import { useAuth } from '../../contexts/AuthContext'
import { errorMessage } from '../../lib/errors'
import { formatCurrency, formatDateTime } from '../../lib/format'
import { useUrlState } from '../../lib/url-state'

function BookingPanel({ doctorId, doctorName, fee }: { doctorId: string; doctorName: string; fee: number }) {
  const { t, i18n } = useTranslation()
  const { user, role } = useAuth()
  const { toast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const { params, set } = useUrlState()
  const slots = useDoctorSlots(doctorId)
  const book = useBookSlot(doctorId)
  const [confirming, setConfirming] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  const day = params.get('day') ?? undefined
  const slotId = params.get('slot') ?? undefined
  const slot = slots.data?.find((item) => item.id === slotId)

  if (slots.isPending) {
    return (
      <div role="status">
        <span className="sr-only">{t('common.loading')}</span>
        <div className="flex gap-2">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-16 w-14" />
          ))}
        </div>
        <Skeleton className="mt-4 h-24" />
      </div>
    )
  }
  if (slots.isError) return <ErrorState error={slots.error} onRetry={() => void slots.refetch()} />
  if (slots.data.length === 0) {
    return (
      <EmptyState
        title={t('booking.noSlotsTitle')}
        description={t('booking.noSlotsBody')}
        action={
          <Button asChild variant="secondary">
            <Link to="/doctors">{t('booking.otherDoctors')}</Link>
          </Button>
        }
      />
    )
  }

  async function confirmBooking() {
    if (!slot) return
    setFailure(null)
    try {
      await book.mutateAsync(slot.id)
      toast(t('booking.booked', { doctor: doctorName, time: formatDateTime(slot.start_time, i18n.language) }))
      navigate('/appointments')
    } catch (error) {
      setConfirming(false)
      setFailure(errorMessage(error, t))
      if (error instanceof ApiError && error.status === 409) set({ slot: undefined }, { replace: true })
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <SlotPicker
        slots={slots.data}
        selectedDay={day}
        selectedSlotId={slotId}
        onDayChange={(next) => set({ day: next, slot: undefined }, { replace: true })}
        onSlotChange={(next) => set({ slot: next }, { replace: true })}
      />

      {failure && <Banner tone="warning">{failure}</Banner>}

      {!user ? (
        <Button asChild>
          <Link to="/login" state={{ from: location }}>
            {t('booking.signInToBook')}
          </Link>
        </Button>
      ) : role !== 'patient' ? (
        <Banner>{t('booking.patientsOnly')}</Banner>
      ) : slot ? (
        <Button onClick={() => setConfirming(true)}>{t('booking.bookThisSlot')}</Button>
      ) : (
        <p aria-live="polite" className="body-6 text-muted">
          {t('booking.pickTime')}
        </p>
      )}

      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        destructive={false}
        title={t('booking.confirmTitle')}
        description={
          slot
            ? t('booking.confirmBody', {
                doctor: doctorName,
                time: formatDateTime(slot.start_time, i18n.language),
                fee: formatCurrency(fee, i18n.language),
              })
            : ''
        }
        confirmLabel={t('booking.confirm')}
        cancelLabel={t('common.goBack')}
        loading={book.isPending}
        onConfirm={() => void confirmBooking()}
      />
    </div>
  )
}

export default function DoctorDetailPage() {
  const { t } = useTranslation()
  const { id = '' } = useParams()
  const doctor = useDoctor(id)

  return (
    <div className="page-gutter py-6 md:py-8">
      <Button asChild variant="link" size="inline" className="mb-4">
        <Link to="/doctors">
          <CaretLeft aria-hidden className="size-4" />
          {t('booking.backToSearch')}
        </Link>
      </Button>

      {doctor.isPending ? (
        <div role="status">
          <span className="sr-only">{t('common.loading')}</span>
          <Skeleton className="h-14 w-72 max-w-full" />
          <Skeleton className="mt-6 h-48" />
        </div>
      ) : doctor.isError ? (
        doctor.error instanceof ApiError && doctor.error.status === 404 ? (
          <EmptyState title={t('booking.notFoundTitle')} description={t('booking.notFoundBody')} />
        ) : (
          <ErrorState error={doctor.error} onRetry={() => void doctor.refetch()} />
        )
      ) : (
        <div className="grid gap-8 lg:grid-cols-12">
          <DoctorCardDetailed doctor={doctor.data} className="lg:col-span-7" />
          <aside aria-labelledby="booking-title" className="min-w-0 lg:col-span-5">
            <div className="rounded-xl border border-border bg-surface p-4 md:p-6 lg:sticky lg:top-[72px]">
              <h2 id="booking-title" className="mb-4 title-2">
                {t('booking.title')}
              </h2>
              <BookingPanel
                doctorId={doctor.data.id}
                doctorName={doctor.data.full_name ?? ''}
                fee={doctor.data.consultation_fee}
              />
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
