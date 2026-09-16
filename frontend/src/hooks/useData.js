import { useCallback, useEffect, useState } from 'react'

/**
 * Minimal data-hook: { data, loading, error, refresh }, refetches when fn or
 * deps change. Call refresh() after a mutation to pull new data.
 */
export function useData(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const [tick, setTick] = useState(0)
  const refresh = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    fn()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null })
      })
      .catch((error) => {
        if (!cancelled) setState({ data: null, loading: false, error })
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fn, ...deps, tick])

  return { ...state, refresh }
}