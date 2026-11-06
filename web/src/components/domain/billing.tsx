import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { formatMonth } from '../../lib/format'
import type { BillingCharge, ChargeStatus } from '../../types'
import { Badge } from '../ui/badge'

const TONES = { owed: 'warning', paid: 'success', waived: 'neutral' } as const

export function ChargeStatusBadge({ status }: { status: ChargeStatus }) {
  const { t } = useTranslation()
  return <Badge tone={TONES[status]}>{t(`billing.chargeStatus.${status}`)}</Badge>
}

/** What a charge was for. It never names a patient. */
export function chargeLabel(charge: BillingCharge, t: TFunction, language: string): string {
  if (charge.kind === 'booking_fee') return t('billing.kind.booking_fee')
  return t('billing.kind.subscription', { month: formatMonth(charge.billing_month ?? charge.created_at, language) })
}
