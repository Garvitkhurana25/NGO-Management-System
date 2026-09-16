// Shared "donate to a campaign" flow, used by the donor dashboard and the
// My Campaigns page so the Razorpay online/offline logic lives in one place.
//
// Returns the paying flag, the campaign waiting on a DonateModal (`donateFor`),
// and handleDonate(campaign, amount) which runs the whole checkout → modal →
// server-side verify dance and then refreshes the caller's data.

import { useState } from 'react'
import { api } from '../api.js'
import { payWithRazorpay } from '../lib/razorpay.js'
import { toast } from '../components/Toast.jsx'

export function useDonate({ refresh } = {}) {
  const [paying, setPaying] = useState(false)
  const [donateFor, setDonateFor] = useState(null)

  async function handleDonate(c, amount) {
    setPaying(true)
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
      toast(
        `Payment successful! Thank you, ${checkout.prefill?.name || 'donor'} for donating ₹${amount.toLocaleString('en-IN')} to “${c.name}”.`,
        'success',
      )
    } catch (err) {
      if (err.code !== 'cancelled') {
        // Donor dismissed the window without paying — stay silent.
        toast(err.message, 'error')
      }
    } finally {
      setPaying(false)
      refresh?.()
    }
  }

  return { paying, donateFor, setDonateFor, handleDonate }
}