import { useTranslation } from 'react-i18next'
import { useDoctorSearch, useSpecialties, useDoctorsSlots } from '../../api/hooks'
import { nextOpenSlot } from '../../lib/slots'
import { DoctorCardCompact } from '../../components/domain/doctor-card'
import { FilterBar } from '../../components/domain/filter-bar'
import { PageHeader } from '../../components/layout/page-header'
import { Combobox } from '../../components/ui/combobox'
import { EmptyState } from '../../components/ui/empty-state'
import { Field } from '../../components/ui/field'
import { Input } from '../../components/ui/input'
import { Pagination } from '../../components/ui/pagination'
import { ErrorState } from '../../components/ui/query-state'
import { Select } from '../../components/ui/select'
import { Skeleton } from '../../components/ui/skeleton'
import { Button } from '../../components/ui/button'
import { useUrlState } from '../../lib/url-state'

const PAGE_SIZE = 10
const SORT_DEFAULT = 'relevance'

function ResultsSkeleton() {
  return (
    <div role="status" className="rounded-xl border border-border bg-surface">
      {[0, 1, 2, 3].map((row) => (
        <div key={row} className="flex gap-3 border-b border-border p-4 last:border-b-0 md:p-4">
          <Skeleton className="size-10 rounded-full" />
          <div className="flex-1">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="mt-2 h-4 w-64 max-w-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function DoctorSearchPage() {
  const { t } = useTranslation()
  const { params, set } = useUrlState()
  const specialties = useSpecialties()

  const specialty = params.get('specialty') ?? ''
  const city = params.get('city') ?? ''
  const maxFee = params.get('max_fee') ?? ''
  const sortBy = params.get('sort_by') ?? ''
  const page = Math.max(1, Number(params.get('page')) || 1)

  const search = useDoctorSearch({
    specialty: specialty || undefined,
    city: city || undefined,
    max_fee: Number(maxFee) > 0 ? Number(maxFee) : undefined,
    sort_by: sortBy || undefined,
    page,
    page_size: PAGE_SIZE,
  })

  const slots = useDoctorsSlots(search.data?.items.map((doctor) => doctor.id) ?? [])
  const activeCount = [specialty, city, maxFee, sortBy].filter(Boolean).length

  function setFilter(changes: Record<string, string>) {
    set({ ...changes, page: undefined })
  }

  return (
    <div className="page-gutter py-6 md:py-8">
      <PageHeader title={t('search.title')} description={t('search.description')} />

      <FilterBar activeCount={activeCount} onClear={() => setFilter({ specialty: '', city: '', max_fee: '', sort_by: '' })}>
        <Field label={t('search.specialty')}>
          {(control) => (
            <Combobox
              {...control}
              value={specialty}
              onValueChange={(value) => setFilter({ specialty: value })}
              options={(specialties.data ?? []).map((item) => ({ value: item.name, label: item.name }))}
              placeholder={t('search.anySpecialty')}
              emptyMessage={t('search.noSpecialty')}
              clearLabel={t('search.clearSpecialty')}
            />
          )}
        </Field>
        <Field label={t('search.city')}>
          {(control) => (
            <Input
              {...control}
              key={city}
              name="city"
              autoComplete="off"
              defaultValue={city}
              placeholder={t('search.cityPlaceholder')}
              onBlur={(event) => setFilter({ city: event.target.value.trim() })}
              onKeyDown={(event) => {
                if (event.key === 'Enter') setFilter({ city: event.currentTarget.value.trim() })
              }}
            />
          )}
        </Field>
        <Field label={t('search.maxFee')}>
          {(control) => (
            <Input
              {...control}
              key={maxFee}
              name="max_fee"
              type="number"
              min={0}
              step={100}
              inputMode="numeric"
              autoComplete="off"
              defaultValue={maxFee}
              onBlur={(event) => setFilter({ max_fee: event.target.value })}
              onKeyDown={(event) => {
                if (event.key === 'Enter') setFilter({ max_fee: event.currentTarget.value })
              }}
            />
          )}
        </Field>
        <Field label={t('search.sort')}>
          {(control) => (
            <Select
              id={control.id}
              value={sortBy || SORT_DEFAULT}
              onValueChange={(value) => setFilter({ sort_by: value === SORT_DEFAULT ? '' : value })}
              options={[
                { value: SORT_DEFAULT, label: t('search.sortNewest') },
                { value: 'fee_asc', label: t('search.sortFeeLow') },
                { value: 'fee_desc', label: t('search.sortFeeHigh') },
                { value: 'experience_desc', label: t('search.sortExperience') },
              ]}
            />
          )}
        </Field>
      </FilterBar>

      <div className="mt-6">
        {search.isPending ? (
          <ResultsSkeleton />
        ) : search.isError ? (
          <ErrorState error={search.error} onRetry={() => void search.refetch()} />
        ) : search.data.items.length === 0 ? (
          <EmptyState
            illustration="search"
            title={t('search.emptyTitle')}
            description={t('search.emptyBody')}
            action={
              activeCount > 0 ? (
                <Button
                  variant="secondary"
                  onClick={() => setFilter({ specialty: '', city: '', max_fee: '', sort_by: '' })}
                >
                  {t('filters.clear')}
                </Button>
              ) : undefined
            }
          />
        ) : (
          <>
            <p className="mb-2 body-6 text-muted" aria-live="polite">
              {t('search.resultCount', { count: search.data.total })}
            </p>
            <ul className="rounded-xl border border-border bg-surface">
              {search.data.items.map((doctor, index) => (
                <li key={doctor.id} className="border-b border-border last:border-b-0">
                  <DoctorCardCompact doctor={doctor} soonest={nextOpenSlot(slots[index]?.data)?.start_time} />
                </li>
              ))}
            </ul>
            <div className="mt-4">
              <Pagination
                page={page}
                pageCount={search.data.total_pages}
                total={search.data.total}
                onPageChange={(next) => set({ page: next })}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
