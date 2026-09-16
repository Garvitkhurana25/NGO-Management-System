import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import StatCard from '../components/StatCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Icon from '../components/Icon.jsx'
import { toast } from '../components/Toast.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'
import { formatINR, formatDate, titleCase } from '../lib/format.js'
import { exportDonationsPdf } from '../lib/exportPdf.js'

/**
 * /me/donations — every transaction a donor has made, with a one-click PDF
 * export of the full statement. Reached from the "Total given" and "Donations"
 * stat cards on the donor dashboard.
 */
export default function MyDonations() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error } = useData(api.myDonations)
  const [exporting, setExporting] = useState(false)

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />
  if (user?.role !== 'donor') return <Navigate to="/" replace />

  const donations = data.results ?? []
  const totalGiven = data.total_given
  const donorName = data.donor?.name ?? user?.username

  async function onExport() {
    setExporting(true)
    try {
      exportDonationsPdf({ donorName, donations, totalGiven })
      toast(
        `Exported ${donations.length} transaction${donations.length === 1 ? '' : 's'} as a PDF.`,
        'success',
      )
    } catch (err) {
      toast(`PDF export failed: ${err.message}`, 'error')
    } finally {
      setExporting(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>My donations</h1>
        <div className="flex" style={{ gap: 8 }}>
          <button className="btn btn-sm" onClick={() => navigate('/')}>
            <Icon name="arrowLeft" size={14} />
            Dashboard
          </button>
          <button className="btn btn-sm btn-primary" onClick={onExport} disabled={exporting}>
            <Icon name="download" size={14} />
            {exporting ? 'Exporting…' : 'Export as PDF'}
          </button>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label="Total given" value={formatINR(totalGiven)} hint="all-time donations" />
        <StatCard label="Transactions" value={donations.length} hint="from your donation history" />
      </div>

      <div className="card">
        {donations.length === 0 ? (
          <p className="small muted">
            You haven’t made any donations yet.{' '}
            <Link to="/me/campaigns">Find a campaign to support</Link>.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Campaign</th>
                  <th className="num">Amount</th>
                  <th>Status</th>
                  <th>Receipt #</th>
                </tr>
              </thead>
              <tbody>
                {donations.map((d) => (
                  <tr key={d.id}>
                    <td className="muted">{formatDate(d.date)}</td>
                    <td>{d.campaign || '—'}</td>
                    <td className="num">{formatINR(d.amount)}</td>
                    <td><StatusBadge status={titleCase(d.status)} /></td>
                    <td className="muted">{d.receipt_number || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}