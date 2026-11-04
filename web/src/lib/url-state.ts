import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

/** Reads and writes query params, so filters, tabs and selection survive Back and reload. */
export function useUrlState() {
  const [params, setParams] = useSearchParams()

  const set = useCallback(
    (changes: Record<string, string | number | undefined | null>, options?: { replace?: boolean }) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current)
          for (const [key, value] of Object.entries(changes)) {
            if (value === undefined || value === null || value === '') next.delete(key)
            else next.set(key, String(value))
          }
          return next
        },
        { replace: options?.replace ?? false }
      )
    },
    [setParams]
  )

  return { params, set }
}
