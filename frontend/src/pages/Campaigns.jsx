import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { useClientFilter } from '../hooks/useClientFilter.js'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'
import FormCard from '../components/FormCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import ProgressBar from '../components/ProgressBar.jsx'
import Icon from '../components/Icon.jsx'
import { confirmAction } from '../components/ConfirmModal.jsx'
import { formatINR, titleCase } from '../lib/format.js'
import { payWithRazorpay } from '../lib/razorpay.js'
import { toast } from '../components/Toast.jsx'
import DonateModal from '../components/DonateModal.jsx'

const EMPTY = { name: '', goal: '', status: 'active', start_date: '', end_date: '', description: '' }

export default function Campaigns() {
  const { user } = useAuth()
  const isDonor = user?.role === 'donor'
  const { data, loading, error, refresh } = useData(api.campaigns)
  const [editing, setEditing] = useState(null)
  const [creating, setCreating] = useState(false)
  const [payingId, setPayingId] = useState(null)
  const [donateFor, setDonateFor] = useState(null)

  const { query, setQuery, filtered } = useClientFilter(
    data?.results ?? [],
    ['name', 'description', 'status'],
  )

  async function submit(values) {
    const body = {
      name: values.name,
      goal: values.goal || '0',
      status: values.status,
      start_date: values.start_date || null,
      end_date: values.end_date || null,
      description: values.description || '',
    }
    if (editing) {
      await api.campaignUpdate(editing.id, body)
      toast('Campaign updated.', 'success')
    } else {
      await api.campaignCreate(body)
      toast('Campaign added.', 'success')
    }
    setEditing(null)
    setCreating(false)
    refresh()
  }

  async function remove(c) {
    const ok = await confirmAction({
      title: `Delete “${c.name}”?`,
      message: 'Linked donations are kept, but the campaign itself is removed.',
      confirmLabel: 'Delete campaign',
      danger: true,
    })
    if (!ok) return
    try {
      await api.campaignDelete(c.id)
      toast('Campaign deleted.', 'info')
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
  }

  async function handleDonate(c, amount) {
    setPayingId(c.id)
    try {
      // 1. Ask the backend to start the donation. It returns mode 'online'
      //    (a Razorpay order was created) or 'offline' (recorded as cash).
      const checkout = await api.donationCheckout(c.id, amount)
      if (checkout.mode === 'offline') {
        toast(
          `Razorpay isn't configured yet, so this was recorded as an offline/cash donation of ₹${amount.toLocaleString('en-IN')}. ` +
            'Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env to enable online payments (see explain.txt).',
          'warning',
        )
        refresh()
        return
      }
      // 2. Online: open the Razorpay payment window for the donor to pay.
      const payment = await payWithRazorpay({
        order_id: checkout.order_id,
        key_id: checkout.key_id,
        amount_paise: checkout.amount_paise,
        currency: checkout.currency,
        name: checkout.name,
        description: checkout.description,
        prefill: checkout.prefill,
      })
      // 3. Re-verify the payment signature on the server, then it's captured.
      await api.donationVerify(checkout.donation_id, payment)
      toast(`Payment successful! Thank you for donating ₹${amount.toLocaleString('en-IN')} to “${c.name}”.`, 'success')
    } catch (err) {
      if (err.code === 'cancelled') {
        // Donor dismissed the payment window without paying — do nothing.
      } else {
        toast(err.message, 'error')
      }
    } finally {
      setPayingId(null)
    }
    refresh()
  }

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  return (
    <>
      <div className="page-head">
        <h1>Campaigns</h1>
        <span className="count-chip">{data.count} campaigns</span>
        {!isDonor && (
          <button className="btn btn-primary u-right" onClick={() => { setCreating(true); setEditing(null) }}>
            <Icon name="plus" size={15} />
            Add campaign
          </button>
        )}
      </div>

      {(creating || editing) && (
        <FormCard
          title={editing ? `Edit ${editing.name}` : 'Add campaign'}
          initial={editing ? { ...editing } : { ...EMPTY }}
          onSubmit={submit}
          onCancel={() => { setCreating(false); setEditing(null) }}
          submitLabel={editing ? 'Save changes' : 'Add campaign'}
        >
          {({ values, set }) => (
            <div className="form-grid">
              <label>
                Name *
                <input value={values.name || ''} onChange={(e) => set('name', e.target.value)} required />
              </label>
              <label>
                Goal (INR)
                <input type="number" min="0" step="0.01" value={values.goal || ''} onChange={(e) => set('goal', e.target.value)} />
              </label>
              <label>
                Status
                <select value={values.status || 'active'} onChange={(e) => set('status', e.target.value)}>
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
              <label>
                Start date
                <input type="date" value={values.start_date || ''} onChange={(e) => set('start_date', e.target.value)} />
              </label>
              <label>
                End date
                <input type="date" value={values.end_date || ''} onChange={(e) => set('end_date', e.target.value)} />
              </label>
              <label className="full">
                Description
                <textarea value={values.description || ''} onChange={(e) => set('description', e.target.value)} />
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
          placeholder="Search campaigns…"
          aria-label="Search campaigns"
        />
      </div>

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Status</th>
              <th className="num">Goal</th>
              <th className="num">Raised</th>
              <th className="num">%</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id}>
                <td>
                  <span className="flex" style={{ alignItems: 'center', gap: 8 }}>
                    <Link to={`/campaigns/${c.id}`}>{c.name}</Link>
                  </span>
                </td>
                <td><StatusBadge status={titleCase(c.status)} /></td>
                <td className="num">{formatINR(c.goal)}</td>
                <td className="num">{formatINR(c.raised)}</td>
                <td className="num">
                  <span style={{ display: 'inline-block', minWidth: 44 }}>{c.progress_percent}%</span>
                  <ProgressBar percent={c.progress_percent} />
                </td>
                <td className="flex" style={{ justifyContent: 'flex-end' }}>
                  {isDonor ? (
                    <button className="btn btn-sm" disabled={payingId !== null} onClick={() => setDonateFor(c)}>
                      {payingId === c.id ? 'Processing…' : 'Donate'}
                    </button>
                  ) : (
                    <>
                      <button className="icon-btn" aria-label={`Edit ${c.name}`} title="Edit" onClick={() => { setEditing(c); setCreating(false) }}>
                        <Icon name="pencil" size={15} />
                      </button>
                      <button className="icon-btn" aria-label={`Delete ${c.name}`} title="Delete" onClick={() => remove(c)}>
                        <Icon name="trash" size={15} />
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="state-block">
                  {query ? `No campaigns match “${query}”.` : 'No campaigns yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {donateFor && (
        <DonateModal
          campaign={donateFor}
          onCancel={() => setDonateFor(null)}
          onConfirm={(amount) => {
            setDonateFor(null)
            handleDonate(donateFor, amount)
          }}
        />
      )}
    </>
  )
}