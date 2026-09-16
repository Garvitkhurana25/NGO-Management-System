import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [authenticated, setAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const payload = await api.me()
      setUser(payload.user)
      setAuthenticated(payload.authenticated)
      setError(null)
    } catch (err) {
      setAuthenticated(false)
      setUser(null)
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const register = useCallback(
    async (body) => {
      setLoading(true)
      try {
        const payload = await api.register(body)
        setUser(payload.user)
        setAuthenticated(true)
        setError(null)
        return { ok: true }
      } catch (err) {
        setError(err)
        setAuthenticated(false)
        return { ok: false, error: err.message }
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const login = useCallback(
    async (username, password) => {
      setLoading(true)
      try {
        const payload = await api.login(username, password)
        setUser(payload.user)
        setAuthenticated(true)
        setError(null)
        return { ok: true }
      } catch (err) {
        setError(err)
        setAuthenticated(false)
        return { ok: false, error: err.message }
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
      setAuthenticated(false)
    }
  }, [])

  const value = {
    user,
    authenticated,
    loading,
    error,
    login,
    register,
    logout,
    refresh,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}