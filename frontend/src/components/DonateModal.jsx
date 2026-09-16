import { useState } from 'react'
import Icon from './Icon.jsx'

/**
 * In-app donate dialog — replaces the browser-native window.prompt so the demo
 * never shows "localhost says". Opens with the campaign, takes an amount, and
 * calls onConfirm(amount) with a validated number.
 */
export default function DonateModal({ campaign, onCancel, onConfirm }) {
  const [amount, setAmount] = useState('100')
  const [error, setError] = useState('')

  function submit() {
    const amt = Number(amount)
    if (!Number.isFinite(amt) || amt <= 0) {
      setError('Enter a valid amount greater than 0.')
      return
    }
    onConfirm(amt)
  }

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-label={`Donate to ${campaign.name}`}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>
          <span className="flex">
            <Icon name="gift" size={18} className="text-brand" />
            Donate to {campaign.name}
          </span>
        </h2>
        <p className="small muted">
          Every rupee goes toward this campaign. If online payment is set up, the payment
          window opens next; otherwise it's recorded as an offline/cash donation.
        </p>
        <label className="donate-amount">
          Amount (INR)
          <input
            type="number"
            min="1"
            step="1"
            value={amount}
            autoFocus
            onChange={(e) => {
              setAmount(e.target.value)
              setError('')
            }}
            onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
          />
        </label>
        {error && <div className="modal-error" role="alert">{error}</div>}
        <div className="flex" style={{ justifyContent: 'flex-end', marginTop: '0.5rem' }}>
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button className="btn btn-primary" onClick={submit}>
            Donate ₹{Number(amount || 0).toLocaleString('en-IN')}
          </button>
        </div>
      </div>
    </div>
  )
}