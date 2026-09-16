import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { useClientFilter } from '../hooks/useClientFilter.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../api.js'
import { Loading, ErrorBlock } from '../components/States.jsx'
import FormCard from '../components/FormCard.jsx'
import Avatar from '../components/Avatar.jsx'
import Icon from '../components/Icon.jsx'
import { confirmAction } from '../components/ConfirmModal.jsx'
import { toast } from '../components/Toast.jsx'
import { formatINR, titleCase } from '../lib/format.js'

const EMPTY = { name: '', donor_type: 'individual', email: '', phone: '', company: '', source: '', tags: '' }

export default function Donors() {
  const { user } = useAuth()
  const canEdit = user?.is_superuser // only the admin edits/deletes donor records
  const { data, loading, error, refresh } = useData(api.donors)
  const [editing, setEditing] = useState(null) // row being edited, or null
  const [creating, setCreating] = useState(false)

  const { query, setQuery, filtered } = useClientFilter(
    data?.results ?? [],
    ['name', 'email', 'company', 'source', 'type'],
  )

  async function submit(values) {
    const body = {
      name: values.name,
      donor_type: values.donor_type,
      email: values.email,
      phone: values.phone,
      company: values.company,
      source: values.source,
      tags: (values.tags || '').split(',').map((t) => t.trim()).filter(Boolean),
    }
    if (editing) {
      await api.donorUpdate(editing.id, body)
      toast('Donor updated.', 'success')
    } else {
      await api.donorCreate(body)
      toast('Donor added.', 'success')
    }
    setEditing(null)
    setCreating(false)
    refresh()
  }

  async function remove(d) {
    const ok = await confirmAction({
      title: `Remove “${d.name}”?`,
      message: 'Their giving history is kept — only the profile is removed.',
      confirmLabel: 'Remove donor',
      danger: true,
    })
    if (!ok) return
    try {
      await api.donorDelete(d.id)
      toast('Donor removed.', 'info')
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
  }

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  function startEdit(row) {
    setEditing(row)
    setCreating(false)
  }

  return (
    <>
      <div className="page-head">
        <h1>Donors</h1>
        <span className="count-chip">{data.count} records</span>
        <button className="btn btn-primary u-right" onClick={() => { setCreating(true); setEditing(null) }}>
          <Icon name="plus" size={15} />
          Add donor
        </button>
      </div>

      {(creating || editing) && (
        <FormCard
          title={editing ? `Edit ${editing.name}` : 'Add donor'}
          initial={
            editing
              ? { ...editing, tags: (editing.tags || []).join(', ') }
              : { ...EMPTY }
          }
          onSubmit={submit}
          onCancel={() => { setCreating(false); setEditing(null) }}
          submitLabel={editing ? 'Save changes' : 'Add donor'}
        >
          {({ values, set }) => (
            <div className="form-grid">
              <label>
                Full name *
                <input value={values.name || ''} onChange={(e) => set('name', e.target.value)} required />
              </label>
              <label>
                Type
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
                <input value={values.source || ''} onChange={(e) => set('source', e.target.value)} placeholder="e.g. website, event, referral" />
              </label>
              <label className="full">
                Tags (comma separated)
                <input value={values.tags || ''} onChange={(e) => set('tags', e.target.value)} placeholder="monthly, major donor" />
              </label>
            </div>
          )}
        </FormCard>
      )}

      <div className="search-box">
        <Icon name="search" size={15} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search donors…"
          aria-label="Search donors"
        />
      </div>

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Email</th>
              <th>Company</th>
              <th className="num">Total given</th>
              <th>Tags</th>
              {canEdit && <th></th>}
            </tr>
          </thead>
          <tbody>
            {filtered.map((d) => (
              <tr key={d.id}>
                <td>
                  <span className="flex" style={{ alignItems: 'center', gap: 8 }}>
                    <Avatar name={d.name} size={28} />
                    <Link to={`/donors/${d.id}`}>{d.name}</Link>
                  </span>
                </td>
                <td className="muted">{titleCase(d.type)}</td>
                <td className="muted">{d.email || '—'}</td>
                <td className="muted">{d.company || '—'}</td>
                <td className="num">{formatINR(d.total_given)}</td>
                <td className="muted">{(d.tags || []).join(', ') || '—'}</td>
                {canEdit && (
                  <td className="flex" style={{ justifyContent: 'flex-end' }}>
                    <button className="icon-btn" aria-label={`Edit ${d.name}`} title="Edit" onClick={() => startEdit(d)}>
                      <Icon name="pencil" size={15} />
                    </button>
                    <button className="icon-btn" aria-label={`Remove ${d.name}`} title="Remove" onClick={() => remove(d)}>
                      <Icon name="trash" size={15} />
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={canEdit ? 7 : 6} className="state-block">
                  {query ? `No donors match “${query}”.` : 'No donors yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}