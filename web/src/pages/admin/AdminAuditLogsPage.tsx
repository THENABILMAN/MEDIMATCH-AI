import { useTranslation } from 'react-i18next'
import { useAuditLogs } from '../../api/hooks'
import { AuditLogTable } from '../../components/domain/audit-log-table'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { Field } from '../../components/ui/field'
import { Input } from '../../components/ui/input'
import { Pagination } from '../../components/ui/pagination'
import { ErrorState } from '../../components/ui/query-state'
import { Select } from '../../components/ui/select'
import { Skeleton } from '../../components/ui/skeleton'
import { PAGE_SIZE } from '../../lib/constants'
import { addDays, dhakaToIso } from '../../lib/format'
import { useTableState } from '../../lib/table-state'

const ACTIONS = [
  'APPROVE_DOCTOR',
  'REJECT_DOCTOR',
  'SUSPEND_DOCTOR',
  'DOCTOR_MATERIAL_PROFILE_UPDATE',
  'UPLOAD_CREDENTIAL',
  'APPOINTMENT_BOOKED',
  'APPOINTMENT_CANCELLED',
  'APPOINTMENT_COMPLETED',
  'REGISTER_PATIENT',
  'REGISTER_DOCTOR',
  'LOGIN_SUCCESS',
  'DELETE_CHAT_HISTORY',
  'ANONYMIZE_PATIENT_ACCOUNT',
]
const ALL = 'all'

export default function AdminAuditLogsPage() {
  const { t } = useTranslation()
  const table = useTableState('created_at', true)
  const action = table.params.get('action') ?? ''
  const from = table.params.get('from') ?? ''
  const to = table.params.get('to') ?? ''

  const logs = useAuditLogs({
    limit: table.limit,
    offset: table.offset,
    action: action || undefined,
    date_from: from ? dhakaToIso(from, '00:00') : undefined,
    date_to: to ? dhakaToIso(addDays(to, 1), '00:00') : undefined,
  })
  const filtered = Boolean(action || from || to)

  return (
    <div className="page-gutter py-4 md:py-6">
      <PageHeader title={t('audit.title')} />
      <div className="mb-4 grid items-end gap-3 md:grid-cols-[1fr_auto_auto_auto]">
        <Field label={t('audit.action')}>
          {(control) => (
            <Select
              id={control.id}
              value={action || ALL}
              onValueChange={(value) => table.set({ action: value === ALL ? undefined : value, page: undefined })}
              options={[
                { value: ALL, label: t('audit.allActions') },
                ...ACTIONS.map((value) => ({ value, label: value })),
              ]}
            />
          )}
        </Field>
        <Field label={t('audit.from')}>
          {(control) => (
            <Input
              {...control}
              type="date"
              value={from}
              max={to || undefined}
              onChange={(event) => table.set({ from: event.target.value, page: undefined })}
            />
          )}
        </Field>
        <Field label={t('audit.to')}>
          {(control) => (
            <Input
              {...control}
              type="date"
              value={to}
              min={from || undefined}
              onChange={(event) => table.set({ to: event.target.value, page: undefined })}
            />
          )}
        </Field>
        <Button
          variant="ghost"
          disabled={!filtered}
          onClick={() => table.set({ action: undefined, from: undefined, to: undefined, page: undefined })}
        >
          {t('filters.clear')}
        </Button>
      </div>
      {logs.isPending ? (
        <Skeleton className="h-80" />
      ) : logs.isError ? (
        <ErrorState error={logs.error} onRetry={() => void logs.refetch()} />
      ) : logs.data.items.length === 0 ? (
        <EmptyState title={t('audit.emptyTitle')} description={t('audit.emptyBody')} />
      ) : (
        <>
          <AuditLogTable logs={logs.data.items} />
          <div className="mt-3">
            <Pagination
              page={table.page}
              pageCount={Math.ceil(logs.data.total / PAGE_SIZE)}
              total={logs.data.total}
              onPageChange={table.setPage}
            />
          </div>
        </>
      )}
    </div>
  )
}
