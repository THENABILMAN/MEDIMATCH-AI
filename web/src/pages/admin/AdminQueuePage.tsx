import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronLeft } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { useAdminDoctors, useDoctorDecision } from '../../api/hooks'
import { CredentialViewer } from '../../components/domain/credential-viewer'
import { VerificationBadge } from '../../components/domain/verification-badge'
import { PageHeader } from '../../components/layout/page-header'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { ConfirmDialog, Dialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { Field } from '../../components/ui/field'
import { Textarea } from '../../components/ui/input'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'
import { Tabs } from '../../components/ui/tabs'
import { useToast } from '../../components/ui/toast'
import { cn } from '../../lib/cn'
import { errorMessage } from '../../lib/errors'
import { formatCurrency, formatDate } from '../../lib/format'
import { useUrlState } from '../../lib/url-state'
import type { AdminDoctor, VerificationStatus } from '../../types'

const STATUSES: VerificationStatus[] = ['pending', 'approved', 'rejected', 'suspended']

function ReasonDialog({
  doctor,
  action,
  onClose,
  onDone,
}: {
  doctor: AdminDoctor
  action: 'reject' | 'suspend'
  onClose: () => void
  onDone: () => void
}) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const decide = useDoctorDecision()
  const schema = useMemo(
    () => z.object({ reason: z.string().trim().min(10, t('queue.reasonRequired')).max(500) }),
    [t]
  )
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<{ reason: string }>({ resolver: zodResolver(schema), mode: 'onBlur' })

  async function onSubmit({ reason }: { reason: string }) {
    try {
      await decide.mutateAsync({ doctorId: doctor.id, action, reason })
      toast(t(`queue.done.${action}`, { doctor: doctor.full_name }))
      onDone()
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t(`queue.${action}Title`, { doctor: doctor.full_name })}
      description={t(`queue.${action}Body`)}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.goBack')}
          </Button>
          <Button type="submit" form="reason-form" variant="danger" loading={decide.isPending}>
            {t(`queue.${action}`)}
          </Button>
        </>
      }
    >
      <form id="reason-form" onSubmit={(event) => void handleSubmit(onSubmit)(event)} noValidate>
        <Field label={t('queue.reason')} hint={t('queue.reasonHint')} error={errors.reason?.message}>
          {(control) => <Textarea {...control} {...register('reason')} />}
        </Field>
      </form>
    </Dialog>
  )
}

function DoctorReview({ doctor, onDecided }: { doctor: AdminDoctor; onDecided: () => void }) {
  const { t, i18n } = useTranslation()
  const { toast } = useToast()
  const decide = useDoctorDecision()
  const [dialog, setDialog] = useState<'approve' | 'reject' | 'suspend' | null>(null)
  const status = doctor.verification_status

  async function approve() {
    try {
      await decide.mutateAsync({ doctorId: doctor.id, action: 'approve' })
      toast(t('queue.done.approve', { doctor: doctor.full_name }))
      setDialog(null)
      onDecided()
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  const facts: [string, string][] = [
    [t('doctor.fee'), formatCurrency(doctor.consultation_fee, i18n.language)],
    [t('doctor.experience'), t('doctor.yearsExperience', { count: doctor.years_experience, years: doctor.years_experience })],
    [t('doctor.location'), [doctor.clinic_name, doctor.city].filter(Boolean).join(', ') || '—'],
    [t('doctor.qualifications'), doctor.qualifications.join(', ') || '—'],
    [t('queue.phone'), doctor.phone ?? '—'],
    [t('queue.applied'), doctor.created_at ? formatDate(doctor.created_at, i18n.language) : '—'],
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold">{doctor.full_name}</h2>
          <p className="text-muted">{doctor.specialties.map((item) => item.name).join(', ') || t('queue.noSpecialties')}</p>
        </div>
        <VerificationBadge status={status} />
      </div>

      <div className="flex flex-wrap gap-2">
        {status !== 'approved' && (
          <Button size="sm" onClick={() => setDialog('approve')}>
            {t(status === 'pending' ? 'queue.approve' : 'queue.reinstate')}
          </Button>
        )}
        {status === 'pending' && (
          <Button variant="danger" size="sm" onClick={() => setDialog('reject')}>
            {t('queue.reject')}
          </Button>
        )}
        {status === 'approved' && (
          <Button variant="danger" size="sm" onClick={() => setDialog('suspend')}>
            {t('queue.suspend')}
          </Button>
        )}
      </div>

      <section aria-labelledby="documents-title">
        <h3 id="documents-title" className="mb-2 text-sm font-semibold">
          {t('queue.documents')}
        </h3>
        {doctor.credentials.length > 0 ? (
          <CredentialViewer credentials={doctor.credentials} />
        ) : (
          <Banner tone="warning">{t('queue.noDocuments')}</Banner>
        )}
      </section>

      <dl className="grid gap-x-6 text-sm md:grid-cols-[auto_1fr]">
        {facts.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="pt-2 text-muted">{label}</dt>
            <dd className="border-b border-border pb-2 md:pt-2 tabular">{value}</dd>
          </div>
        ))}
      </dl>
      {doctor.bio && <p className="prose-width text-sm">{doctor.bio}</p>}

      <ConfirmDialog
        open={dialog === 'approve'}
        onOpenChange={(open) => !open && setDialog(null)}
        destructive={false}
        title={t('queue.approveTitle', { doctor: doctor.full_name })}
        description={t('queue.approveBody')}
        confirmLabel={t('queue.approve')}
        cancelLabel={t('common.goBack')}
        loading={decide.isPending}
        onConfirm={() => void approve()}
      />
      {(dialog === 'reject' || dialog === 'suspend') && (
        <ReasonDialog doctor={doctor} action={dialog} onClose={() => setDialog(null)} onDone={onDecided} />
      )}
    </div>
  )
}

export default function AdminQueuePage() {
  const { t } = useTranslation()
  const { params, set } = useUrlState()
  const status = (STATUSES as string[]).includes(params.get('status') ?? '')
    ? (params.get('status') as VerificationStatus)
    : 'pending'
  const doctors = useAdminDoctors({ status, limit: 100, offset: 0, sort: 'created_at', descending: false })
  const selectedId = params.get('doctor')
  const items = doctors.data?.items ?? []
  const selected = items.find((doctor) => doctor.id === selectedId)

  function linkFor(id: string) {
    const next = new URLSearchParams(params)
    next.set('doctor', id)
    return `?${next.toString()}`
  }

  return (
    <div className="page-gutter py-4 md:py-6">
      <PageHeader title={t('queue.title')} />
      <Tabs
        value={status}
        onValueChange={(next) => set({ status: next === 'pending' ? undefined : next, doctor: undefined })}
        tabs={STATUSES.map((item) => ({ value: item, label: t(`verification.status.${item}`) }))}
      >
        {doctors.isPending ? (
          <Skeleton className="h-80" />
        ) : doctors.isError ? (
          <ErrorState error={doctors.error} onRetry={() => void doctors.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title={t(`queue.empty.${status}.title`)} description={t(`queue.empty.${status}.body`)} />
        ) : (
          <div className="grid gap-4 lg:grid-cols-12">
            <nav
              aria-label={t('queue.list')}
              className={cn(
                'min-w-0 lg:col-span-4 lg:block',
                selected && 'hidden'
              )}
            >
              <ul className="max-h-[70dvh] overflow-y-auto rounded-md border border-border bg-surface">
                {items.map((doctor) => (
                  <li key={doctor.id} className="border-b border-border last:border-b-0">
                    <Link
                      to={linkFor(doctor.id)}
                      aria-current={doctor.id === selectedId ? 'true' : undefined}
                      className="block p-3 transition-colors hover:bg-canvas aria-[current=true]:bg-primary-tint"
                    >
                      <span className="block font-medium">{doctor.full_name}</span>
                      <span className="block text-sm text-muted">
                        {doctor.specialties.map((item) => item.name).join(', ') || t('queue.noSpecialties')}
                      </span>
                      <span className="block text-sm text-muted">
                        {t('queue.documentCount', { count: doctor.credentials.length })}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
            <section aria-label={t('queue.review')} className={cn('min-w-0 lg:col-span-8', !selected && 'hidden lg:block')}>
              {selected ? (
                <div className="rounded-md border border-border bg-surface p-4 md:p-6">
                  <Button
                    variant="link"
                    size="inline"
                    className="mb-3 lg:hidden"
                    onClick={() => set({ doctor: undefined })}
                  >
                    <ChevronLeft aria-hidden className="size-4" strokeWidth={1.75} />
                    {t('queue.backToList')}
                  </Button>
                  <DoctorReview key={selected.id} doctor={selected} onDecided={() => set({ doctor: undefined })} />
                </div>
              ) : (
                <EmptyState title={t('queue.selectTitle')} description={t('queue.selectBody')} />
              )}
            </section>
          </div>
        )}
      </Tabs>
    </div>
  )
}
