import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Clock3, RefreshCw, Send, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import { claimsApi, getApiError, type MetricsResponse } from '../api'

export function AdminPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  async function load() {
    setError('')
    try { setMetrics(await claimsApi.metrics()); setUnavailable(false) }
    catch (cause) { setMetrics(null); setUnavailable(true); setError(getApiError(cause)) }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  const cards = [
    ['Total claims', metrics?.total_claims, <Send size={15}/>],
    ['Pending', metrics?.pending_claims, <Clock3 size={15}/>],
    ['Completed', metrics?.completed_claims, <CheckCircle2 size={15}/>],
    ['Failed', metrics?.failed_claims, <AlertTriangle size={15}/>],
    ['Processing', metrics?.processing_claims, <Activity size={15}/>],
    ['Escalated', metrics?.escalated_claims, <TrendingUp size={15}/>],
  ] as const

  return <div className="page"><div className="page-heading"><span className="eyebrow">Operations overview</span><h1>Claim dashboard</h1><p>Live counts and recent submissions reported by the backend.</p></div>{error && <div className="api-error">Metrics unavailable: {error}</div>}
    <div className="metrics-grid">{cards.map(([label,value,icon])=><article className="metric-card" key={label}><div className="metric-label">{icon}{label}</div><div className="metric-value">{loading ? '—' : unavailable ? 'Not available' : value}</div><div className="metric-caption">{unavailable ? 'API metric unavailable' : 'Current persisted count'}</div></article>)}</div>
    <section className="panel"><div className="panel-head"><h2>Recent submissions</h2><button className="button-secondary" onClick={() => { setLoading(true); void load() }}><RefreshCw size={13}/> Refresh</button></div>{loading ? <div className="skeleton"/> : unavailable ? <div className="empty-state"><Activity size={22}/><strong>Recent claims unavailable</strong><p>Connect to the backend to load live operational metrics.</p></div> : metrics?.recent_claims.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Claim ID</th><th>Flight</th><th>Status</th><th>Submitted</th><th></th></tr></thead><tbody>{metrics.recent_claims.map(item=><tr key={item.claim_id}><td className="mono">{item.claim_id}</td><td>{item.flight_number || '—'}</td><td><span className={`status-pill ${item.status}`}><i className="status-dot"/>{item.status}</span></td><td>{new Date(item.created_at).toLocaleString()}</td><td><Link className="link-button" to={item.status === 'completed' ? `/result/${encodeURIComponent(item.claim_id)}` : `/track?claimId=${encodeURIComponent(item.claim_id)}`}>View</Link></td></tr>)}</tbody></table></div> : <div className="empty-state"><Send size={22}/><strong>No claims submitted yet</strong><p>Submitted claims will appear here.</p></div>}</section>
  </div>
}
