import { useParams, Link } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { api } from '../api.js'
import { Loading, ErrorBlock } from '../components/States.jsx'
import Avatar from '../components/Avatar.jsx'
import Icon from '../components/Icon.jsx'
import { formatINR, titleCase } from '../lib/format.js'

export default function DonorDetail() {
  const { id } = useParams()
  const { data, loading, error } = useData(() => api.donor(id), [id])

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  const timeline = data.timeline ?? []
  const tags = data.tags ?? []

  return (
    <>
      <div className="page-head">
        <Link to="/donors" className="btn btn-sm btn-ghost">
          <Icon name="arrowLeft" size={14} />
          Donors
        </Link>
      </div>

      <div className="chart-grid">
        <div className="card">
          <div className="donor-hero">
            <Avatar name={data.name} size={56} />
            <div>
              <strong>{data.name}</strong>
              <small>{titleCase(data.type)}{data.company ? ` · ${data.company}` : ''}</small>
            </div>
          </div>

          <dl className="kv-grid">
            <div className="kv">
              <dt>Total given</dt>
              <dd><strong className="text-brand">{formatINR(data.total_given)}</strong></dd>
            </div>
            <div className="kv">
              <dt>Email</dt>
              <dd>{data.email || '—'}</dd>
            </div>
            <div className="kv">
              <dt>Phone</dt>
              <dd>{data.phone || '—'}</dd>
            </div>
            <div className="kv">
              <dt>Source</dt>
              <dd>{data.source || '—'}</dd>
            </div>
          </dl>

          {tags.length > 0 && (
            <>
              <div className="small muted" style={{ marginBottom: 6 }}>Tags</div>
              <div className="tag-chips">
                {tags.map((t) => (
                  <span key={t} className="tag-chip">{t}</span>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="card">
          <h2>Timeline</h2>
          {timeline.length === 0 ? (
            <div className="muted">No activity yet.</div>
          ) : (
            <ul className="timeline">
              {timeline.map((e, i) => (
                <li key={i}>
                  <div className="t-title">{e.detail}</div>
                  <div className="t-meta">
                    {e.kind ? `${titleCase(e.kind)} · ` : ''}
                    {e.at ? new Date(e.at).toLocaleString('en-IN') : ''}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}