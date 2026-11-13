import type { TFunction } from 'i18next'
import { formatCurrency, formatNumber } from '../../lib/format'

/** A fee, or that it is not listed. An unknown fee is never shown as free. */
export function feeText(fee: number | null | undefined, t: TFunction, language: string): string {
  return fee ? formatCurrency(fee, language) : t('doctor.feeNotListed')
}

/** Years of experience, or nothing when the listing does not say. */
export function experienceText(years: number | null | undefined, t: TFunction, language: string): string | null {
  if (years === null || years === undefined) return null
  return t('doctor.yearsExperience', { count: years, years: formatNumber(years, language) })
}

/** A doctor listed from a public directory, whom MediMatch has not verified and who has no online booking. */
export function isDirectoryListing(doctor: { listing_source?: string | null }): boolean {
  return doctor.listing_source === 'directory'
}
