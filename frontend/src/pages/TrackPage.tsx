import { FormEvent, useCallback, useEffect, useState } from 'react'
import { ArrowRight, Clock3, RefreshCw, Search, ShieldAlert } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { claimsApi, getApiError, type ClaimStatusResponse } from '../api'

function Status({ status }: { status: ClaimStatusResponse['status'] }) {
  return <span className={`status-pill ${status}`}><i className="status-dot"/>{status}</span>
}

export function TrackPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialId = searchParams.get('claimId') ?? ''
  const [claimId, setClaimId] = useState(initialId)
  const [activeId, setActiveId] = useState(initialId)
  const [record, setRecord] = useState<ClaimStatusResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const refresh = useCallback(async (id: string, showBusy = true) => {
    if (!id.trim()) { setError('Enter the claim ID from your submission confirmation.'); return }
    if (showBusy) setBusy(true)
    setError('')
    try {
      const data = await claimsApi.status(id.trim())
      setRecord(data)
      setActiveId(id.trim())
      setSearchParams({ claimId: id.trim() }, { replace: true })
    } catch (cause) { setRecord(null); setError(getApiError(cause)) }
    finally { if (showBusy) setBusy(false) }
  }, [setSearchParams])

  useEffect(() => { if (initialId) void refresh(initialId) }, [initialId, refresh])
  useEffect(() => {
    if (!activeId || !record || !['pending', 'processing'].includes(record.status)) return
    const timer = window.setInterval(() => { void refresh(activeId, false) }, 3500)
    return () => window.clearInterval(timer)
  }, [activeId, record?.status, refresh])

  function submit(event: FormEvent) { event.preventDefault(); void refresh(claimId) }

  return <div className="page"><div className="page-heading"><span className="eyebrow">Claim lookup</span><h1>Track your claim</h1><p>Enter the claim ID you received when you submitted your request.</p></div><section className="panel track-card"><form className="search-row" onSubmit={submit}><input aria-label="Claim ID" className="search-input" value={claimId} onChange={e => setClaimId(e.target.value)} placeholder="Paste your claim ID"/><button type="submit" className="button-primary" disabled={busy}>{busy ? <span className="spinner"/> : <Search size={15}/>} Find claim</button></form>{error && <div className="api-error" role="alert" style={{marginTop:14,marginBottom:0}}>{error}</div>}
    {record && <div className="tracking-result"><div className="track-meta"><div><span className="muted">Claim ID</span><div className="mono" style={{color:'#385b78',marginTop:5}}>{record.claim_id}</div></div><Status status={record.status}/></div><div className="track-meta" style={{marginTop:18}}><span className="muted">Submitted {new Date(record.created_at).toLocaleString()}</span><button className="link-button" onClick={() => void refresh(activeId)}><RefreshCw size={12} style={{verticalAlign:'middle',marginRight:5}}/>Refresh</button></div>
      {['pending','processing'].includes(record.status) && <p className="muted" style={{marginTop:18,display:'flex',alignItems:'center',gap:8}}><span className="spinner"/>Status refreshes automatically every few seconds.</p>}
      {record.status === 'completed' && <div style={{marginTop:18}}><Link className="button-primary" to={`/result/${encodeURIComponent(record.claim_id)}`}>View claim result <ArrowRight size={15}/></Link></div>}
      {record.status === 'failed' && <div className="api-error" style={{marginTop:18,marginBottom:0}}><ShieldAlert size={14} style={{verticalAlign:'middle',marginRight:6}}/>{record.failure_message || 'Processing failed. Please contact the project team.'}</div>}
    </div>}
    {!record && !error && <div className="empty-state"><Clock3 size={23}/><strong>Your status will appear here</strong><p>We’ll show the latest state associated with your claim ID.</p></div>}
  </section></div>
}
