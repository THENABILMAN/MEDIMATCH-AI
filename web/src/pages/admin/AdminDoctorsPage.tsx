import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useAdminDoctors } from '../../api/hooks'
import { VerificationBadge } from '../../components/domain/verification-badge'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { Pagination } from '../../components/ui/pagination'
import { ErrorState } from '../../components/ui/query-state'
import { Select } from '../../components/ui/select'
import { Skeleton } from '../../components/ui/skeleton'
import { SortableHeader, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { PAGE_SIZE } from '../../lib/constants'
import { formatCurrency } from '../../lib/format'
import { useTableState } from '../../lib/table-state'
import type { VerificationStatus } from '../../types'

const STATUSES: VerificationStatus[] = ['pending', 'approved', 'rejected', 'suspended']
const ALL = 'all'

export default function AdminDoctorsPage() {
  const { t, i18n } = useTranslation()
  const table = useTableState('created_at', true)
  const statusParam = table.params.get('status') as VerificationStatus | null
  const doctors = useAdminDoctors({
    status: statusParam ?? undefined,
    limit: table.limit,
    offset: table.offset,
    sort: table.sort,
    descending: table.descending,
  })

  return (
    <div className="page-gutter py-4 md:py-6">
      <PageHeader
        title={t('adminDoctors.title')}
        actions={
          <Select
            aria-label={t('adminDoctors.filterStatus')}
            className="w-48"
            value={statusParam ?? ALL}
            onValueChange={(value) => table.set({ status: value === ALL ? undefined : value, page: undefined })}
            options={[
              { value: ALL, label: t('adminDoctors.allStatuses') },
              ...STATUSES.map((value) => ({ value, label: t(`verification.status.${value}`) })),
            ]}
          />
        }
      />
      {doctors.isPending ? (
        <Skeleton className="h-80" />
      ) : doctors.isError ? (
        <ErrorState error={doctors.error} onRetry={() => void doctors.refetch()} />
      ) : doctors.data.items.length === 0 ? (
        <EmptyState title={t('adminDoctors.emptyTitle')} description={t('adminDoctors.emptyBody')} />
      ) : (
        <>
          <Table caption={t('adminDoctors.title')}>
            <TableHead>
              <tr>
                <TableHeader>{t('adminDoctors.name')}</TableHeader>
                <TableHeader className="hidden lg:table-cell">{t('adminDoctors.specialties')}</TableHeader>
                <SortableHeader
                  className="hidden md:table-cell"
                  direction={table.direction('city')}
                  onSort={() => table.toggleSort('city')}
                >
                  {t('adminDoctors.city')}
                </SortableHeader>
                <SortableHeader
                  numeric
                  className="hidden md:table-cell"
                  direction={table.direction('years_experience')}
                  onSort={() => table.toggleSort('years_experience')}
                >
                  {t('adminDoctors.experience')}
                </SortableHeader>
                <SortableHeader
                  numeric
                  className="hidden md:table-cell"
                  direction={table.direction('consultation_fee')}
                  onSort={() => table.toggleSort('consultation_fee')}
                >
                  {t('adminDoctors.fee')}
                </SortableHeader>
                <SortableHeader
                  direction={table.direction('verification_status')}
                  onSort={() => table.toggleSort('verification_status')}
                >
                  {t('adminDoctors.status')}
                </SortableHeader>
                <TableHeader>
                  <span className="sr-only">{t('adminDoctors.actions')}</span>
                </TableHeader>
              </tr>
            </TableHead>
            <TableBody>
              {doctors.data.items.map((doctor) => (
                <TableRow key={doctor.id}>
                  <TableCell className="font-medium">{doctor.full_name}</TableCell>
                  <TableCell className="hidden min-w-40 text-muted lg:table-cell">
                    {doctor.specialties.map((item) => item.name).join(', ')}
                  </TableCell>
                  <TableCell className="hidden md:table-cell">{doctor.city}</TableCell>
                  <TableCell className="hidden text-right tabular md:table-cell">{doctor.years_experience}</TableCell>
                  <TableCell className="hidden text-right tabular md:table-cell">
                    {formatCurrency(doctor.consultation_fee, i18n.language)}
                  </TableCell>
                  <TableCell>
                    <VerificationBadge status={doctor.verification_status} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button asChild variant="secondary" size="sm">
                      <Link
                        to={`/admin/queue?status=${doctor.verification_status}&doctor=${doctor.id}`}
                        aria-label={t('adminDoctors.reviewNamed', { doctor: doctor.full_name })}
                      >
                        {t('adminDoctors.review')}
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="mt-3">
            <Pagination
              page={table.page}
              pageCount={Math.ceil(doctors.data.total / PAGE_SIZE)}
              total={doctors.data.total}
              onPageChange={table.setPage}
            />
          </div>
        </>
      )}
    </div>
  )
}
