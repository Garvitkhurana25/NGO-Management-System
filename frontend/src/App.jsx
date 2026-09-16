import { Navigate, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './auth/ProtectedRoute.jsx'
import { useAuth } from './auth/AuthContext.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import VolunteerDashboard from './pages/VolunteerDashboard.jsx'
import DonorDashboard from './pages/DonorDashboard.jsx'
import MyDonations from './pages/MyDonations.jsx'
import MyCampaigns from './pages/MyCampaigns.jsx'
import MyProfile from './pages/MyProfile.jsx'
import Donors from './pages/Donors.jsx'
import DonorDetail from './pages/DonorDetail.jsx'
import Donations from './pages/Donations.jsx'
import Campaigns from './pages/Campaigns.jsx'
import CampaignDetail from './pages/CampaignDetail.jsx'
import Volunteers from './pages/Volunteers.jsx'
import Events from './pages/Events.jsx'
import Users from './pages/Users.jsx'

/**
 * The "/" index is role-aware: volunteers and donors land on a personal
 * dashboard with only the actions their role allows; staff and superusers keep
 * the full analytics Dashboard.
 */
function RoleHome() {
  const { user } = useAuth()
  if (user?.role === 'volunteer') return <VolunteerDashboard />
  if (user?.role === 'donor') return <DonorDashboard />
  return <Dashboard />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<RoleHome />} />
        <Route path="me/donations" element={<ProtectedRoute><MyDonations /></ProtectedRoute>} />
        <Route path="me/campaigns" element={<ProtectedRoute><MyCampaigns /></ProtectedRoute>} />
        <Route path="me/profile" element={<ProtectedRoute><MyProfile /></ProtectedRoute>} />
        <Route path="donors" element={<ProtectedRoute staff><Donors /></ProtectedRoute>} />
        <Route path="donors/:id" element={<ProtectedRoute staff><DonorDetail /></ProtectedRoute>} />
        <Route path="donations" element={<ProtectedRoute staff><Donations /></ProtectedRoute>} />
        <Route path="campaigns" element={<ProtectedRoute staff><Campaigns /></ProtectedRoute>} />
        <Route path="campaigns/:id" element={<ProtectedRoute staff><CampaignDetail /></ProtectedRoute>} />
        <Route path="volunteers" element={<ProtectedRoute staff><Volunteers /></ProtectedRoute>} />
        <Route path="events" element={<ProtectedRoute staff><Events /></ProtectedRoute>} />
        <Route
          path="users"
          element={
            <ProtectedRoute superuser>
              <Users />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}