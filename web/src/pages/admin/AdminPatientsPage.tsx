import { useTranslation } from 'react-i18next'
import { useAdminPatients } from '../../api/hooks'
import { PageHeader } from '../../components/layout/page-header'
import { EmptyState } from '../../components/ui/empty-state'
import { Input } from '../../components/ui/input'
import { Pagination } from '../../components/ui/pagination'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'
import { SortableHeader, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { PAGE_SIZE } from '../../lib/constants'
import { formatDate } from '../../lib/format'
import { useTableState } from '../../lib/table-state'

export default function AdminPatientsPage() {
  const { t, i18n } = useTranslation()
  const table = useTableState('created_at', true)
  const search = table.params.get('q') ?? ''
  const patients = useAdminPatients({
    limit: table.limit,
    offset: table.offset,
    sort: table.sort,
    descending: table.descending,
    search: search || undefined,
  })

  return (
    <div className="page-gutter py-4 md:py-6">
      <PageHeader
        title={t('patients.title')}
        actions={
          <Input
            key={search}
            type="search"
            aria-label={t('patients.search')}
            placeholder={t('patients.searchPlaceholder')}
            defaultValue={search}
            autoComplete="off"
            className="w-full md:w-64"
            onBlur={(event) => table.set({ q: event.target.value.trim(), page: undefined })}
            onKeyDown={(event) => {
              if (event.key === 'Enter') table.set({ q: event.currentTarget.value.trim(), page: undefined })
            }}
          />
        }
      />
      {patients.isPending ? (
        <Skeleton className="h-80" />
      ) : patients.isError ? (
        <ErrorState error={patients.error} onRetry={() => void patients.refetch()} />
      ) : patients.data.items.length === 0 ? (
        <EmptyState title={t('patients.emptyTitle')} description={t('patients.emptyBody')} />
      ) : (
        <>
          <Table caption={t('patients.title')}>
            <TableHead>
              <tr>
                <SortableHeader direction={table.direction('full_name')} onSort={() => table.toggleSort('full_name')}>
                  {t('patients.name')}
                </SortableHeader>
                <TableHeader>{t('patients.phone')}</TableHeader>
                <TableHeader className="hidden text-right md:table-cell">{t('patients.appointments')}</TableHeader>
                <SortableHeader
                  className="hidden md:table-cell"
                  direction={table.direction('created_at')}
                  onSort={() => table.toggleSort('created_at')}
                >
                  {t('patients.joined')}
                </SortableHeader>
              </tr>
            </TableHead>
            <TableBody>
              {patients.data.items.map((patient) => (
                <TableRow key={patient.id}>
                  <TableCell className="body-5">{patient.full_name}</TableCell>
                  <TableCell className="tabular">{patient.phone ?? '—'}</TableCell>
                  <TableCell className="hidden text-right tabular md:table-cell">{patient.appointment_count}</TableCell>
                  <TableCell className="hidden whitespace-nowrap tabular md:table-cell">
                    {patient.created_at ? formatDate(patient.created_at, i18n.language) : '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="mt-3">
            <Pagination
              page={table.page}
              pageCount={Math.ceil(patients.data.total / PAGE_SIZE)}
              total={patients.data.total}
              onPageChange={table.setPage}
            />
          </div>
        </>
      )}
    </div>
  )
}
