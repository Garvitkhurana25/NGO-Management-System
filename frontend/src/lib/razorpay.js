// Razorpay Checkout — loads the official checkout script on demand and wraps
// the payment modal in a Promise, so callers get the payment response (or an
// error) without threading callbacks.
//
// The modal is Razorpay-hosted: the donor pays inside it and never enters card
// details on our site. On success we hand the response (order_id + payment_id
// + signature) back to the page, which posts it to the backend for server-side
// signature verification before the donation is marked captured.

let checkoutPromise = null

// Inject https://checkout.razorpay.com/v1/checkout.js the first time it's
// needed, resolve window.Razorpay once loaded.
function loadRazorpay() {
  if (typeof window !== 'undefined' && window.Razorpay) {
    return Promise.resolve(window.Razorpay)
  }
  if (checkoutPromise) return checkoutPromise
  checkoutPromise = new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = 'https://checkout.razorpay.com/v1/checkout.js'
    s.async = true
    s.onload = () => resolve(window.Razorpay)
    s.onerror = () => {
      checkoutPromise = null
      reject(new Error("Couldn't load the Razorpay payment window. Check your internet connection."))
    }
    document.head.appendChild(s)
  })
  return checkoutPromise
}

/**
 * Open the Razorpay payment modal for a created order.
 *
 * @param {object} opts — from the /checkout/ endpoint:
 *   { order_id, key_id, amount_paise, currency, name, description, prefill }
 * @returns {Promise<{razorpay_order_id, razorpay_payment_id, razorpay_signature}>}
 *   resolves on successful payment; rejects with `code: 'cancelled'` when the
 *   donor dismisses the window without paying.
 */
export async function payWithRazorpay(opts) {
  const Razorpay = await loadRazorpay()
  return new Promise((resolve, reject) => {
    const rzp = new Razorpay({
      key: opts.key_id,
      amount: opts.amount_paise,
      currency: opts.currency || 'INR',
      name: opts.name || 'NGO Platform',
      description: opts.description || 'Donation',
      order_id: opts.order_id,
      prefill: opts.prefill || {},
      theme: { color: '#2a78d6' },
      modal: {
        ondismiss: () =>
          reject(Object.assign(new Error('Payment window closed.'), { code: 'cancelled' })),
      },
      handler: (response) =>
        resolve({
          razorpay_order_id: response.razorpay_order_id,
          razorpay_payment_id: response.razorpay_payment_id,
          razorpay_signature: response.razorpay_signature,
        }),
    })
    // A payment that fails after the donor submits (declined card, insufficient
    // balance, timeout) never calls `handler` — Razorpay fires this instead.
    rzp.on('payment.failed', (response) =>
      reject(
        Object.assign(
          new Error(
            response?.error?.description || 'Payment failed — please try a different method.',
          ),
          { code: 'failed' },
        ),
      ),
    )
    rzp.open()
  })
}