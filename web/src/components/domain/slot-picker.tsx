import { RadioGroup as RadioPrimitive } from 'radix-ui'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/cn'
import { dhakaDay, formatDayNumber, formatShortDate, formatTime, formatWeekday } from '../../lib/format'
import type { AvailabilitySlot } from '../../types'

const itemClasses =
  'rounded-lg border border-control bg-surface transition-colors hover:border-ink data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-white '

interface SlotPickerProps {
  slots: AvailabilitySlot[]
  selectedDay?: string
  selectedSlotId?: string
  onDayChange: (day: string) => void
  onSlotChange: (slotId: string) => void
}

/** Arrow keys move through days and times, because both are radio groups. */
export function SlotPicker({ slots, selectedDay, selectedSlotId, onDayChange, onSlotChange }: SlotPickerProps) {
  const { t, i18n } = useTranslation()

  const days = useMemo(() => {
    const grouped = new Map<string, AvailabilitySlot[]>()
    for (const slot of slots) {
      const day = dhakaDay(slot.start_time)
      grouped.set(day, [...(grouped.get(day) ?? []), slot])
    }
    return [...grouped.entries()]
  }, [slots])

  const activeDay = days.some(([day]) => day === selectedDay) ? selectedDay : days[0]?.[0]
  const times = days.find(([day]) => day === activeDay)?.[1] ?? []

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <RadioPrimitive.Root
        aria-label={t('booking.chooseDay')}
        value={activeDay}
        onValueChange={onDayChange}
        orientation="horizontal"
        className="flex gap-2 overflow-x-auto pb-1"
      >
        {days.map(([day, daySlots]) => (
          <RadioPrimitive.Item
            key={day}
            value={day}
            aria-label={formatShortDate(daySlots[0].start_time, i18n.language)}
            className={cn(itemClasses, 'flex min-h-16 w-14 shrink-0 flex-col items-center justify-center')}
          >
            <span className="caption-5">{formatWeekday(daySlots[0].start_time, i18n.language)}</span>
            <span className="title-2 tabular">
              {formatDayNumber(daySlots[0].start_time, i18n.language)}
            </span>
          </RadioPrimitive.Item>
        ))}
      </RadioPrimitive.Root>

      <RadioPrimitive.Root
        aria-label={t('booking.chooseTime')}
        value={selectedSlotId ?? ''}
        onValueChange={onSlotChange}
        className="grid grid-cols-3 gap-2"
      >
        {times.map((slot) => (
          <RadioPrimitive.Item
            key={slot.id}
            value={slot.id}
            className={cn(itemClasses, 'h-11 px-1 body-5 tabular')}
          >
            {formatTime(slot.start_time, i18n.language)}
          </RadioPrimitive.Item>
        ))}
      </RadioPrimitive.Root>

      <p className="body-6 text-muted">{t('booking.timezone')}</p>
    </div>
  )
}
