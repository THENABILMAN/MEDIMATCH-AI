import type { AvailabilitySlot } from '../types'

export function nextOpenSlot(slots: AvailabilitySlot[] = []): AvailabilitySlot | undefined {
  return slots
    .filter((slot) => !slot.is_booked && new Date(slot.start_time) > new Date())
    .sort((a, b) => a.start_time.localeCompare(b.start_time))[0]
}
