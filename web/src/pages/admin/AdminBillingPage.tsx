import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { useAdminCharges, usePricing, useSavePricing, useSettleCharge } from '../../api/hooks'
import { ChargeStatusBadge, chargeLabel } from '../../components/domain/billing'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { ConfirmDialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { Field } from '../../components/ui/field'
import { Input } from '../../components/ui/input'
import { Pagination } from '../../components/ui/pagination'
import { ErrorState } from '../../components/ui/query-state'
import { Select } from '../../components/ui/select'
import { Skeleton } from '../../components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { useToast } from '../../components/ui/toast'
import { PAGE_SIZE } from '../../lib/constants'
import { errorMessage } from '../../lib/errors'
import { formatCurrency, formatDate } from '../../lib/format'
import { useTableState } from '../../lib/table-state'
import type { AdminBillingCharge, BillingPricing, ChargeStatus } from '../../types'

const STATUSES: ChargeStatus[] = ['owed', 'paid', 'waived']
const ALL = 'all'
const MAX_PRICE = 1_000_000

type PriceValues = Record<keyof BillingPricing, string>

const toText = (price: number | null) => (price === null ? '' : String(price))
const toPrice = (text: string) => (text.trim() === '' ? null : Number(text))

function PricingForm({ pricing }: { pricing: BillingPricing }) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const save = useSavePricing()
  const schema = useMemo(() => {
    const price = z
      .string()
      .trim()
      .refine((text) => text === '' || (/^\d+$/.test(text) && Number(text) > 0 && Number(text) <= MAX_PRICE), {
        message: t('billing.priceInvalid'),
      })
    return z.object({ booking_fee_bdt: price, subscription_monthly_bdt: price })
  }, [t])
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PriceValues>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
    defaultValues: {
      booking_fee_bdt: toText(pricing.booking_fee_bdt),
      subscription_monthly_bdt: toText(pricing.subscription_monthly_bdt),
    },
  })

  useEffect(() => {
    reset({
      booking_fee_bdt: toText(pricing.booking_fee_bdt),
      subscription_monthly_bdt: toText(pricing.subscription_monthly_bdt),
    })
  }, [pricing, reset])

  async function onSubmit(values: PriceValues) {
    try {
      await save.mutateAsync({
        booking_fee_bdt: toPrice(values.booking_fee_bdt),
        subscription_monthly_bdt: toPrice(values.subscription_monthly_bdt),
      })
      toast(t('billing.pricesSaved'))
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <form
      onSubmit={(event) => void handleSubmit(onSubmit)(event)}
      noValidate
      aria-labelledby="prices-title"
      className="rounded-xl border border-border bg-surface p-4 md:p-6"
    >
      <h2 id="prices-title" className="heading-6">
        {t('billing.pricesTitle')}
      </h2>
      <p className="body-6 mt-1 text-muted">{t('billing.pricesHint')}</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Field label={t('billing.bookingFeeField')} error={errors.booking_fee_bdt?.message}>
          {(control) => <Input {...control} inputMode="numeric" autoComplete="off" {...register('booking_fee_bdt')} />}
        </Field>
        <Field label={t('billing.subscriptionField')} error={errors.subscription_monthly_bdt?.message}>
          {(control) => (
            <Input {...control} inputMode="numeric" autoComplete="off" {...register('subscription_monthly_bdt')} />
          )}
        </Field>
      </div>
      <Button type="submit" className="mt-4" loading={save.isPending}>
        {t('billing.savePrices')}
      </Button>
    </form>
  )
}

export default function AdminBillingPage() {
  const { t, i18n } = useTranslation()
  const { toast } = useToast()
  const table = useTableState('created_at', true)
  const statusParam = table.params.get('status') as ChargeStatus | null
  const pricing = usePricing()
  const charges = useAdminCharges({ status: statusParam ?? undefined, limit: table.limit, offset: table.offset })
  const settle = useSettleCharge()
  const [settling, setSettling] = useState<{ charge: AdminBillingCharge; outcome: 'paid' | 'waived' } | null>(null)

  const money = (amount: number) => formatCurrency(amount, i18n.language)

  async function confirmSettle() {
    if (!settling) return
    try {
      await settle.mutateAsync({ id: settling.charge.id, status: settling.outcome })
      toast(t(`billing.settled.${settling.outcome}`))
      setSettling(null)
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <div className="page-gutter py-4 md:py-6">
      <PageHeader title={t('billing.adminTitle')} description={t('billing.adminLead')} />

      {pricing.isPending ? (
        <Skeleton className="h-48" />
      ) : pricing.isError ? (
        <ErrorState error={pricing.error} onRetry={() => void pricing.refetch()} />
      ) : (
        <PricingForm pricing={pricing.data} />
      )}

      <section aria-labelledby="charges-title" className="mt-8">
        <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 id="charges-title" className="heading-5">
            {t('billing.chargesTitle')}
          </h2>
          <Select
            aria-label={t('billing.filterStatus')}
            className="w-48"
            value={statusParam ?? ALL}
            onValueChange={(value) => table.set({ status: value === ALL ? undefined : value, page: undefined })}
            options={[
              { value: ALL, label: t('billing.allStatuses') },
              ...STATUSES.map((value) => ({ value, label: t(`billing.chargeStatus.${value}`) })),
            ]}
          />
        </div>

        {charges.isPending ? (
          <Skeleton className="h-64" />
        ) : charges.isError ? (
          <ErrorState error={charges.error} onRetry={() => void charges.refetch()} />
        ) : charges.data.items.length === 0 ? (
          <EmptyState title={t('billing.adminEmptyTitle')} description={t('billing.adminEmptyBody')} />
        ) : (
          <>
            <Table caption={t('billing.chargesTitle')}>
              <TableHead>
                <tr>
                  <TableHeader>{t('billing.date')}</TableHeader>
                  <TableHeader>{t('billing.doctor')}</TableHeader>
                  <TableHeader>{t('billing.charge')}</TableHeader>
                  <TableHeader>{t('billing.amount')}</TableHeader>
                  <TableHeader>{t('billing.status')}</TableHeader>
                  <TableHeader>
                    <span className="sr-only">{t('adminDoctors.actions')}</span>
                  </TableHeader>
                </tr>
              </TableHead>
              <TableBody>
                {charges.data.items.map((charge) => (
                  <TableRow key={charge.id}>
                    <TableCell className="whitespace-nowrap">{formatDate(charge.created_at, i18n.language)}</TableCell>
                    <TableCell className="body-5">{charge.doctor_name}</TableCell>
                    <TableCell>{chargeLabel(charge, t, i18n.language)}</TableCell>
                    <TableCell className="tabular">{money(charge.amount_bdt)}</TableCell>
                    <TableCell>
                      <ChargeStatusBadge status={charge.status} />
                    </TableCell>
                    <TableCell>
                      {charge.status === 'owed' && (
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="secondary" onClick={() => setSettling({ charge, outcome: 'paid' })}>
                            {t('billing.markPaid')}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setSettling({ charge, outcome: 'waived' })}>
                            {t('billing.waive')}
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination
              page={table.page}
              pageCount={Math.ceil(charges.data.total / PAGE_SIZE)}
              total={charges.data.total}
              onPageChange={table.setPage}
            />
          </>
        )}
      </section>

      <ConfirmDialog
        open={settling !== null}
        onOpenChange={(open) => !open && setSettling(null)}
        title={t(`billing.settleTitle.${settling?.outcome ?? 'paid'}`)}
        description={t('billing.settleBody', {
          amount: settling ? money(settling.charge.amount_bdt) : '',
          doctor: settling?.charge.doctor_name ?? '',
        })}
        confirmLabel={t(`billing.settleAction.${settling?.outcome ?? 'paid'}`)}
        cancelLabel={t('common.cancel')}
        destructive={false}
        loading={settle.isPending}
        onConfirm={() => void confirmSettle()}
      />
    </div>
  )
}
