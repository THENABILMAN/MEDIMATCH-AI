import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useChooseBillingPlan, useMyBilling } from '../../api/hooks'
import { ChargeStatusBadge, chargeLabel } from '../../components/domain/billing'
import { PageHeader } from '../../components/layout/page-header'
import { RadioGroup } from '../../components/ui/choice'
import { ConfirmDialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { useToast } from '../../components/ui/toast'
import { errorMessage } from '../../lib/errors'
import { formatCurrency, formatDate } from '../../lib/format'
import type { BillingPlan } from '../../types'

export default function DoctorBillingPage() {
  const { t, i18n } = useTranslation()
  const { toast } = useToast()
  const billing = useMyBilling()
  const choose = useChooseBillingPlan()
  const [pending, setPending] = useState<BillingPlan | null>(null)

  const money = (amount: number) => formatCurrency(amount, i18n.language)
  const priceLine = (amount: number | null | undefined, unit: string) =>
    amount ? `${money(amount)} ${unit}` : t('billing.priceLater')

  async function confirmPlan() {
    if (!pending) return
    try {
      await choose.mutateAsync(pending)
      toast(t('billing.planSaved', { plan: t(`billing.plan.${pending}.title`) }))
      setPending(null)
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  if (billing.isPending) {
    return (
      <div className="page-gutter py-4 md:py-6">
        <PageHeader title={t('billing.title')} />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (billing.isError) {
    return (
      <div className="page-gutter py-4 md:py-6">
        <PageHeader title={t('billing.title')} />
        <ErrorState error={billing.error} onRetry={() => void billing.refetch()} />
      </div>
    )
  }

  const { plan, pricing, total_owed_bdt: owed, charges } = billing.data
  const monthly = pricing.subscription_monthly_bdt

  return (
    <div className="page-gutter py-4 md:py-6">
      <PageHeader title={t('billing.title')} description={t('billing.lead')} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <section aria-labelledby="plan-title" className="rounded-xl border border-border bg-surface p-4 md:p-6">
          <h2 id="plan-title" className="heading-6">
            {t('billing.chooseTitle')}
          </h2>
          <RadioGroup
            className="mt-3"
            aria-labelledby="plan-title"
            value={plan ?? ''}
            onValueChange={(value) => setPending(value as BillingPlan)}
            options={[
              {
                value: 'booking_fee',
                label: `${t('billing.plan.booking_fee.title')}: ${priceLine(pricing.booking_fee_bdt, t('billing.perAppointment'))}`,
                description: t('billing.plan.booking_fee.body'),
              },
              {
                value: 'subscription',
                label: `${t('billing.plan.subscription.title')}: ${priceLine(monthly, t('billing.perMonth'))}`,
                description: t('billing.plan.subscription.body'),
              },
            ]}
          />
        </section>

        <section aria-labelledby="owed-title" className="rounded-xl border border-border bg-surface p-4 md:p-6">
          <h2 id="owed-title" className="heading-6">
            {t('billing.owedTitle')}
          </h2>
          <p className="heading-3 mt-2 tabular">{money(owed)}</p>
          <p className="body-6 mt-2 text-muted">{t('billing.howToPay')}</p>
        </section>
      </div>

      <section aria-labelledby="charges-title" className="mt-8">
        <h2 id="charges-title" className="heading-5 mb-3">
          {t('billing.chargesTitle')}
        </h2>
        {charges.length === 0 ? (
          <EmptyState title={t('billing.emptyTitle')} description={t('billing.emptyBody')} />
        ) : (
          <Table caption={t('billing.chargesTitle')}>
            <TableHead>
              <tr>
                <TableHeader>{t('billing.date')}</TableHeader>
                <TableHeader>{t('billing.charge')}</TableHeader>
                <TableHeader>{t('billing.amount')}</TableHeader>
                <TableHeader>{t('billing.status')}</TableHeader>
              </tr>
            </TableHead>
            <TableBody>
              {charges.map((charge) => (
                <TableRow key={charge.id}>
                  <TableCell className="whitespace-nowrap">{formatDate(charge.created_at, i18n.language)}</TableCell>
                  <TableCell>{chargeLabel(charge, t, i18n.language)}</TableCell>
                  <TableCell className="tabular">{money(charge.amount_bdt)}</TableCell>
                  <TableCell>
                    <ChargeStatusBadge status={charge.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>

      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={t('billing.confirmTitle', { plan: pending ? t(`billing.plan.${pending}.title`) : '' })}
        description={
          pending === 'subscription' && monthly
            ? t('billing.confirmSubscription', { amount: money(monthly) })
            : t('billing.confirmBody')
        }
        confirmLabel={t('billing.confirmAction')}
        cancelLabel={t('common.cancel')}
        destructive={false}
        loading={choose.isPending}
        onConfirm={() => void confirmPlan()}
      />
    </div>
  )
}
