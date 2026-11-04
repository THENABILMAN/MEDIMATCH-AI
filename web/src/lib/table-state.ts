import { useCallback } from 'react'
import type { SortDirection } from '../components/ui/table'
import { PAGE_SIZE } from './constants'
import { useUrlState } from './url-state'

/** Sort and page for an admin table, kept in the URL. */
export function useTableState(defaultSort: string, defaultDescending: boolean) {
  const { params, set } = useUrlState()
  const sort = params.get('sort') ?? defaultSort
  const descending = params.has('dir') ? params.get('dir') === 'desc' : defaultDescending
  const page = Math.max(1, Number(params.get('page')) || 1)

  const toggleSort = useCallback(
    (column: string) => {
      const nextDescending = column === sort ? !descending : false
      set({ sort: column, dir: nextDescending ? 'desc' : 'asc', page: undefined })
    },
    [descending, set, sort]
  )

  const direction = useCallback(
    (column: string): SortDirection | undefined =>
      column === sort ? (descending ? 'descending' : 'ascending') : undefined,
    [descending, sort]
  )

  return {
    params,
    set,
    sort,
    descending,
    page,
    offset: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
    toggleSort,
    direction,
    setPage: (next: number) => set({ page: next }),
  }
}
