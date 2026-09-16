import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import { Loading } from '../components/States.jsx'

/**
 * Gates a route behind a Django session. While the initial /auth/me/ probe is
 * in flight we render a loading state; once known, redirect to /login for
 * anonymous users. `staff` further requires is_staff (mutations). `superuser`
 * requires is_superuser (user management page).
 */
export default function ProtectedRoute({ children, staff = false, superuser = false }) {
  const { authenticated, loading, user } = useAuth()

  if (loading) {
    return (
      <div className="main-center">
        <Loading label="Checking session…" />
      </div>
    )
  }

  if (!authenticated) {
    return <Navigate to="/login" replace />
  }

  if (superuser && !user?.is_superuser) {
    return <Navigate to="/" replace />
  }

  if (staff && !user?.is_staff) {
    return <Navigate to="/" replace />
  }

  return children
}