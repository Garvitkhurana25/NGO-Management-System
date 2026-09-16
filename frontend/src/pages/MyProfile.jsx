import { Navigate, useNavigate } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import FormCard from '../components/FormCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Icon from '../components/Icon.jsx'
import { toast } from '../components/Toast.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'

/**
 * /me/profile — standalone edit page for the logged-in donor or volunteer's own
 * profile. Lives on its own route instead of an inline form on the dashboard.
 * Field sets mirror what me_profile_update accepts per role.
 */
export default function MyProfile() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error } = useData(api.meSummary)
  const role = data?.role ?? user?.role

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />
  if (role !== 'donor' && role !== 'volunteer') return <Navigate to="/" replace />

  const profile = data.profile ?? {}

  async function saveProfile(values) {
    await api.meProfileUpdate(values)
    toast('Profile updated.', 'success')
    navigate('/')
  }

  const back = (
    <button className="btn btn-sm" onClick={() => navigate('/')}>
      <Icon name="arrowLeft" size={14} />
      Back to dashboard
    </button>
  )

  if (role === 'volunteer') {
    return (
      <>
        <div className="page-head">
          <h1>Edit profile</h1>
          {back}
        </div>
        <FormCard
          title="My profile"
          initial={{
            name: profile?.name ?? '',
            email: profile?.email ?? '',
            phone: profile?.phone ?? '',
            skills: profile?.skills ?? '',
          }}
          onSubmit={saveProfile}
          onCancel={() => navigate('/')}
          submitLabel="Save profile"
        >
          {({ values, set }) => (
            <div className="form-grid">
              <label>
                Full name
                <input value={values.name || ''} onChange={(e) => set('name', e.target.value)} required />
              </label>
              <label>
                Email
                <input type="email" value={values.email || ''} onChange={(e) => set('email', e.target.value)} />
              </label>
              <label>
                Phone
                <input value={values.phone || ''} onChange={(e) => set('phone', e.target.value)} />
              </label>
              <label className="full">
                Skills / interests
                <input
                  value={values.skills || ''}
                  onChange={(e) => set('skills', e.target.value)}
                  placeholder="teaching, events, fundraising"
                />
              </label>
              <p className="small muted full">
                Background check: <StatusBadge status={profile?.background_check_status} /> — reviewed by our team.
              </p>
            </div>
          )}
        </FormCard>
      </>
    )
  }

  return (
    <>
      <div className="page-head">
        <h1>Edit profile</h1>
        {back}
      </div>
      <FormCard
        title="My profile"
        initial={{
          name: profile?.name ?? '',
          email: profile?.email ?? '',
          phone: profile?.phone ?? '',
          donor_type: profile?.donor_type ?? 'individual',
          company: profile?.company ?? '',
          source: profile?.source ?? '',
        }}
        onSubmit={saveProfile}
        onCancel={() => navigate('/')}
        submitLabel="Save profile"
      >
        {({ values, set }) => (
          <div className="form-grid">
            <label>
              Full name
              <input value={values.name || ''} onChange={(e) => set('name', e.target.value)} required />
            </label>
            <label>
              Donor type
              <select value={values.donor_type || 'individual'} onChange={(e) => set('donor_type', e.target.value)}>
                <option value="individual">Individual</option>
                <option value="organization">Organization</option>
              </select>
            </label>
            <label>
              Email
              <input type="email" value={values.email || ''} onChange={(e) => set('email', e.target.value)} />
            </label>
            <label>
              Phone
              <input value={values.phone || ''} onChange={(e) => set('phone', e.target.value)} />
            </label>
            <label>
              Company
              <input value={values.company || ''} onChange={(e) => set('company', e.target.value)} />
            </label>
            <label>
              Source
              <input value={values.source || ''} onChange={(e) => set('source', e.target.value)} placeholder="how did you hear about us" />
            </label>
          </div>
        )}
      </FormCard>
    </>
  )
}