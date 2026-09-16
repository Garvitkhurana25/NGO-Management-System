import { useMemo, useState } from 'react'

/**
 * Client-side filter for list pages. `fields` are the row keys searched.
 * Returns { query, setQuery, filtered } — no API round-trip.
 */
export function useClientFilter(list = [], fields = []) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return list
    return list.filter((row) =>
      fields.some((f) => {
        const v = row?.[f]
        return String(v ?? '')
          .toLowerCase()
          .includes(q)
      }),
    )
  }, [list, query, fields])

  return { query, setQuery, filtered }
}