import { useData } from '../hooks/useData.js'
import { useClientFilter } from '../hooks/useClientFilter.js'
import { api } from '../api.js'
import { Loading, ErrorBlock } from '../components/States.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Avatar from '../components/Avatar.jsx'
import Icon from '../components/Icon.jsx'
import { formatINR, titleCase, formatDate } from '../lib/format.js'

export default function Donations() {
  const { data, loading, error } = useData(api.donations)

  const { query, setQuery, filtered } = useClientFilter(
    data?.results ?? [],
    ['receipt_number', 'donor', 'campaign'],
  )

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  return (
    <>
      <div className="page-head">
        <h1>Donations</h1>
        <span className="count-chip">{data.count} records</span>
      </div>
      <div className="search-box">
        <Icon name="search" size={15} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search donations…"
          aria-label="Search donations"
        />
      </div>
      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Receipt</th>
              <th>Donor</th>
              <th>Campaign</th>
              <th className="num">Amount</th>
              <th>Status</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((d) => (
              <tr key={d.id}>
                <td className="muted">{d.receipt_number || `#${d.id}`}</td>
                <td>
                  <span className="flex" style={{ alignItems: 'center', gap: 8 }}>
                    <Avatar name={d.donor} size={26} />
                    {d.donor}
                  </span>
                </td>
                <td className="muted">{d.campaign || '—'}</td>
                <td className="num">{formatINR(d.amount)}</td>
                <td><StatusBadge status={titleCase(d.status)} /></td>
                <td className="muted">{formatDate(d.date)}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="state-block">
                  {query ? `No donations match “${query}”.` : 'No donations yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}