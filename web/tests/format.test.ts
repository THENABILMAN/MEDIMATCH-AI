import { describe, expect, it } from 'vitest'
import { addDays, dhakaDay, dhakaToIso, formatCurrency, formatDate, formatTime, startOfWeek } from '../src/lib/format'

describe('formatting', () => {
  it('shows fees in Taka without decimals', () => {
    expect(formatCurrency(1500)).toBe('৳1,500')
  })

  it('shows times in Dhaka, whatever the device timezone', () => {
    expect(formatTime('2026-11-05T04:30:00Z')).toBe('10:30 am')
  })

  it('uses the Dhaka calendar day near midnight UTC', () => {
    expect(dhakaDay('2026-11-05T20:00:00Z')).toBe('2026-11-06')
    expect(formatDate('2026-11-05T20:00:00Z')).toContain('6 Nov')
  })

  it('converts a Dhaka time to the correct instant', () => {
    expect(dhakaToIso('2026-11-05', '10:30')).toBe('2026-11-05T04:30:00.000Z')
  })

  it('moves across month ends and finds Monday', () => {
    expect(addDays('2026-11-30', 1)).toBe('2026-12-01')
    expect(startOfWeek('2026-11-05')).toBe('2026-11-02')
    expect(startOfWeek('2026-11-08')).toBe('2026-11-02')
  })
})
