const TIME_ZONE = 'Asia/Dhaka'

function intlLocale(language: string): string {
  return language.startsWith('bn') ? 'bn-BD' : 'en-GB'
}

export function formatCurrency(amount: number, language = 'en'): string {
  return new Intl.NumberFormat(intlLocale(language), {
    style: 'currency',
    currency: 'BDT',
    currencyDisplay: 'narrowSymbol',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatNumber(value: number, language = 'en'): string {
  return new Intl.NumberFormat(intlLocale(language)).format(value)
}

function format(iso: string, language: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat(intlLocale(language), { timeZone: TIME_ZONE, ...options }).format(
    new Date(iso)
  )
}

export function formatDate(iso: string, language = 'en'): string {
  return format(iso, language, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatMonth(iso: string, language = 'en'): string {
  return format(iso, language, { month: 'long', year: 'numeric' })
}

export function formatShortDate(iso: string, language = 'en'): string {
  return format(iso, language, { day: 'numeric', month: 'short' })
}

export function formatWeekday(iso: string, language = 'en'): string {
  return format(iso, language, { weekday: 'short' })
}

export function formatDayNumber(iso: string, language = 'en'): string {
  return format(iso, language, { day: 'numeric' })
}

export function formatTime(iso: string, language = 'en'): string {
  return format(iso, language, { hour: 'numeric', minute: '2-digit', hour12: true })
}

export function formatDateTime(iso: string, language = 'en'): string {
  return `${formatDate(iso, language)}, ${formatTime(iso, language)}`
}

/** The calendar day in Dhaka as YYYY-MM-DD, for grouping and URL state. */
export function dhakaDay(iso: string | Date): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso
  return new Intl.DateTimeFormat('en-CA', { timeZone: TIME_ZONE }).format(date)
}

/** Converts a Dhaka calendar day and HH:MM into an ISO instant. Dhaka has no daylight saving. */
export function dhakaToIso(day: string, time: string): string {
  return new Date(`${day}T${time}:00+06:00`).toISOString()
}

/** Adds whole days to a YYYY-MM-DD string. */
export function addDays(day: string, days: number): string {
  const date = new Date(`${day}T12:00:00+06:00`)
  date.setUTCDate(date.getUTCDate() + days)
  return dhakaDay(date)
}

/** Monday of the week containing the given Dhaka day. */
export function startOfWeek(day: string): string {
  const weekday = new Date(`${day}T12:00:00+06:00`).getUTCDay()
  return addDays(day, -((weekday + 6) % 7))
}
