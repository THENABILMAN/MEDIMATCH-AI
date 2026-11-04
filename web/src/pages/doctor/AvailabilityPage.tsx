import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronLeft, ChevronRight, Lock, Plus, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { useCreateSlot, useDeleteSlot, useMyDoctorProfile, useMySlots } from '../../api/hooks'
import { PageHeader } from '../../components/layout/page-header'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { ConfirmDialog, Dialog } from '../../components/ui/dialog'
import { Field } from '../../components/ui/field'
import { IconButton } from '../../components/ui/icon-button'
import { Input } from '../../components/ui/input'
import { ErrorState } from '../../components/ui/query-state'
import { Select } from '../../components/ui/select'
import { Skeleton } from '../../components/ui/skeleton'
import { useToast } from '../../components/ui/toast'
import { errorMessage } from '../../lib/errors'
import {
  addDays,
  dhakaDay,
  dhakaToIso,
  formatDayNumber,
  formatShortDate,
  formatTime,
  formatWeekday,
  startOfWeek,
} from '../../lib/format'
import { useUrlState } from '../../lib/url-state'
import type { AvailabilitySlot } from '../../types'

const DURATIONS = ['15', '20', '30', '45', '60']

interface SlotValues {
  day: string
  time: string
  minutes: string
}

function isPast(iso: string): boolean {
  return iso <= new Date().toISOString()
}

function overlapping(slots: AvailabilitySlot[], start: string, end: string) {
  return slots.find((slot) => slot.start_time < end && slot.end_time > start)
}

function SlotBlock({ slot, onDelete }: { slot: AvailabilitySlot; onDelete: () => void }) {
  const { t, i18n } = useTranslation()
  const time = formatTime(slot.start_time, i18n.language)
  return (
    <li
      className={
        slot.is_booked
          ? 'flex min-h-11 items-center justify-between gap-1 rounded-sm bg-primary-tint pl-2 text-sm text-primary-hover'
          : 'flex min-h-11 items-center justify-between gap-1 rounded-sm border border-border pl-2 text-sm'
      }
    >
      <span className="tabular">
        {time} – {formatTime(slot.end_time, i18n.language)}
      </span>
      {slot.is_booked ? (
        <span className="flex size-11 items-center justify-center md:size-10" title={t('availability.booked')}>
          <Lock aria-hidden className="size-4" strokeWidth={1.75} />
          <span className="sr-only">{t('availability.booked')}</span>
        </span>
      ) : (
        <IconButton label={t('availability.deleteNamed', { time })} onClick={onDelete}>
          <Trash2 aria-hidden className="size-4" strokeWidth={1.75} />
        </IconButton>
      )}
    </li>
  )
}

export default function AvailabilityPage() {
  const { t, i18n } = useTranslation()
  const { toast } = useToast()
  const { params, set } = useUrlState()
  const profile = useMyDoctorProfile()
  const slots = useMySlots()
  const create = useCreateSlot()
  const remove = useDeleteSlot()
  const [adding, setAdding] = useState(false)
  const [deleting, setDeleting] = useState<AvailabilitySlot | null>(null)
  const [today] = useState(() => dhakaDay(new Date()))

  const week = startOfWeek(params.get('week') ?? today)
  const days = useMemo(() => Array.from({ length: 7 }, (_, index) => addDays(week, index)), [week])
  const allSlots = useMemo(() => slots.data ?? [], [slots.data])

  const schema = useMemo(
    () =>
      z
        .object({ day: z.string().min(1), time: z.string().min(1, t('availability.timeRequired')), minutes: z.string() })
        .superRefine((values, context) => {
          if (!values.time) return
          const start = dhakaToIso(values.day, values.time)
          const end = new Date(new Date(start).getTime() + Number(values.minutes) * 60000).toISOString()
          if (isPast(start)) {
            context.addIssue({ code: 'custom', path: ['time'], message: t('availability.inPast') })
          } else if (overlapping(allSlots, start, end)) {
            context.addIssue({ code: 'custom', path: ['time'], message: t('availability.overlap') })
          }
        }),
    [allSlots, t]
  )

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SlotValues>({ resolver: zodResolver(schema), mode: 'onChange' })

  useEffect(() => {
    if (adding) return
    reset({ day: today, time: '', minutes: '30' })
  }, [adding, reset, today])

  function openForm(day: string) {
    reset({ day, time: '', minutes: '30' })
    setAdding(true)
  }

  async function addSlot(values: SlotValues) {
    const start = dhakaToIso(values.day, values.time)
    const end = new Date(new Date(start).getTime() + Number(values.minutes) * 60000).toISOString()
    try {
      await create.mutateAsync({ start, end })
      toast(t('availability.added'))
      setAdding(false)
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  async function confirmDelete() {
    if (!deleting) return
    try {
      await remove.mutateAsync(deleting.id)
      toast(t('availability.deleted'))
      setDeleting(null)
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  const approved = profile.data?.verification_status === 'approved'

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader
        title={t('availability.title')}
        description={t('availability.description')}
        actions={
          approved ? (
            <Button onClick={() => openForm(days.find((day) => day >= today) ?? week)}>
              <Plus aria-hidden className="size-4" strokeWidth={1.75} />
              {t('availability.add')}
            </Button>
          ) : undefined
        }
      />

      {profile.data && !approved && (
        <Banner tone="warning" className="mb-4">
          {t('availability.notApproved')}
        </Banner>
      )}

      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-md font-semibold whitespace-nowrap tabular md:text-lg" aria-live="polite">
          {t('availability.weekOf', { date: formatShortDate(`${week}T12:00:00+06:00`, i18n.language) })}
        </h2>
        <div className="flex gap-2">
          <IconButton variant="outline" label={t('availability.previousWeek')} onClick={() => set({ week: addDays(week, -7) })}>
            <ChevronLeft aria-hidden className="size-5" strokeWidth={1.75} />
          </IconButton>
          <Button variant="secondary" onClick={() => set({ week: undefined })}>
            {t('availability.thisWeek')}
          </Button>
          <IconButton variant="outline" label={t('availability.nextWeek')} onClick={() => set({ week: addDays(week, 7) })}>
            <ChevronRight aria-hidden className="size-5" strokeWidth={1.75} />
          </IconButton>
        </div>
      </div>

      {slots.isPending ? (
        <Skeleton className="h-64" />
      ) : slots.isError ? (
        <ErrorState error={slots.error} onRetry={() => void slots.refetch()} />
      ) : (
        <div className="grid overflow-hidden rounded-md border border-border bg-surface lg:grid-cols-7">
          {days.map((day) => {
            const iso = `${day}T12:00:00+06:00`
            const daySlots = allSlots
              .filter((slot) => dhakaDay(slot.start_time) === day)
              .sort((a, b) => a.start_time.localeCompare(b.start_time))
            const past = day < today
            return (
              <section
                key={day}
                aria-label={formatShortDate(iso, i18n.language)}
                className="flex min-w-0 flex-col gap-2 border-b border-border p-3 last:border-b-0 lg:min-h-64 lg:border-r lg:border-b-0 lg:last:border-r-0"
              >
                <div className="flex min-h-11 items-center justify-between gap-2 md:min-h-10">
                  <p className={day === today ? 'font-semibold text-primary-hover' : 'font-medium'}>
                    {formatWeekday(iso, i18n.language)} <span className="tabular">{formatDayNumber(iso, i18n.language)}</span>
                  </p>
                  {approved && !past && (
                    <IconButton label={t('availability.addOn', { date: formatShortDate(iso, i18n.language) })} onClick={() => openForm(day)}>
                      <Plus aria-hidden className="size-4" strokeWidth={1.75} />
                    </IconButton>
                  )}
                </div>
                {daySlots.length > 0 ? (
                  <ul className="flex flex-col gap-1">
                    {daySlots.map((slot) => (
                      <SlotBlock key={slot.id} slot={slot} onDelete={() => setDeleting(slot)} />
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted">{t('availability.none')}</p>
                )}
              </section>
            )
          })}
        </div>
      )}
      <p className="mt-2 text-sm text-muted">{t('booking.timezone')}</p>
      {allSlots.length === 0 && slots.isSuccess && approved && (
        <p className="mt-2 text-muted">{t('availability.emptyHint')}</p>
      )}

      <Dialog
        open={adding}
        onOpenChange={setAdding}
        title={t('availability.addTitle')}
        description={t('booking.timezone')}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAdding(false)}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" form="slot-form" loading={create.isPending}>
              {t('availability.addConfirm')}
            </Button>
          </>
        }
      >
        <form
          id="slot-form"
          onSubmit={(event) => void handleSubmit(addSlot)(event)}
          noValidate
          className="flex flex-col gap-4"
        >
          <Field label={t('availability.day')} error={errors.day?.message}>
            {(field) => <Input {...field} type="date" min={today} {...register('day')} />}
          </Field>
          <Field label={t('availability.startTime')} error={errors.time?.message}>
            {(field) => <Input {...field} type="time" step={300} {...register('time')} />}
          </Field>
          <Field label={t('availability.duration')}>
            {(field) => (
              <Controller
                control={control}
                name="minutes"
                render={({ field: { value, onChange } }) => (
                  <Select
                    id={field.id}
                    value={value ?? '30'}
                    onValueChange={onChange}
                    options={DURATIONS.map((minutes) => ({
                      value: minutes,
                      label: t('availability.minutes', { count: Number(minutes) }),
                    }))}
                  />
                )}
              />
            )}
          </Field>
        </form>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title={t('availability.deleteTitle')}
        description={t('availability.deleteBody', {
          time: deleting ? formatTime(deleting.start_time, i18n.language) : '',
          date: deleting ? formatShortDate(deleting.start_time, i18n.language) : '',
        })}
        confirmLabel={t('availability.delete')}
        cancelLabel={t('common.goBack')}
        loading={remove.isPending}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  )
}
