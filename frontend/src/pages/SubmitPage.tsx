import { FormEvent, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, CircleHelp, FileText, Info, LoaderCircle, ShieldCheck } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { claimsApi, getApiError, type ClaimPayload } from '../api'

export function SubmitPage() {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [accepted, setAccepted] = useState<{ claim_id: string; created_at: string } | null>(null)
  const [form, setForm] = useState<ClaimPayload>({ complaint: '', flight_number: '', disruption_type: '', scheduled_time: '', actual_time: '' })
  const update = (key: keyof ClaimPayload, value: string) => setForm(current => ({ ...current, [key]: value }))

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    const complaint = form.complaint.trim()
    if (!complaint) { setError('Please describe what happened on your flight.'); return }
    if (complaint.length > 10_000) { setError('Your description must be 10,000 characters or fewer.'); return }
    if (form.flight_number?.trim() && !/^[A-Za-z0-9]{2,3}\s?-?\d{1,4}$/.test(form.flight_number.trim())) {
      setError('Enter a flight number such as AI245 or UK 123.')
      return
    }
    setBusy(true)
    try {
      const payload: ClaimPayload = { complaint }
      if (form.flight_number?.trim()) payload.flight_number = form.flight_number.trim()
      if (form.disruption_type) payload.disruption_type = form.disruption_type
      if (form.scheduled_time) payload.scheduled_time = form.scheduled_time
      if (form.actual_time) payload.actual_time = form.actual_time
      const result = await claimsApi.submit(payload)
      setAccepted({ claim_id: result.claim_id, created_at: result.created_at })
    } catch (cause) { setError(getApiError(cause)) }
    finally { setBusy(false) }
  }

  if (accepted) return <div className="page"><div className="page-heading"><span className="eyebrow">Claim received</span><h1>Your claim is in the queue</h1></div><section className="form-card success-card"><span className="success-icon"><Check size={25}/></span><h2>Submission accepted</h2><p className="muted">Your claim was saved. Keep this ID to check its progress.</p><div className="claim-id-box">{accepted.claim_id}</div><p className="muted">Submitted {new Date(accepted.created_at).toLocaleString()}</p><div className="inline-actions"><button className="button-primary" onClick={() => navigate(`/track?claimId=${encodeURIComponent(accepted.claim_id)}`)}>Track this claim <ArrowRight size={15}/></button><button className="button-secondary" onClick={() => { setAccepted(null); setForm({ complaint: '', flight_number: '', disruption_type: '', scheduled_time: '', actual_time: '' }) }}>Submit another</button></div></section></div>

  return <div className="page"><div className="page-heading"><Link className="text-link" to="/" style={{marginBottom:14}}><ArrowLeft size={14}/> Back to overview</Link><span className="eyebrow">Start a review</span><h1>Tell us about your flight</h1><p>Share the details you have. Optional fields can be left blank.</p></div><div className="form-layout"><form className="form-card" onSubmit={submit} noValidate><h2>Flight details</h2><p className="form-intro">We’ll use these details to organize a preliminary claim review.</p>{error && <div className="api-error" role="alert">{error}</div>}<div className="form-grid">
    <div className="field"><label htmlFor="flight">Flight number <span>· optional</span></label><input id="flight" value={form.flight_number ?? ''} onChange={e => update('flight_number', e.target.value)} placeholder="e.g. AI245" maxLength={32}/><small>Airline code followed by the flight number.</small></div>
    <div className="field"><label htmlFor="disruption">Disruption type <span>· optional</span></label><select id="disruption" value={form.disruption_type ?? ''} onChange={e => update('disruption_type', e.target.value)}><option value="">Select a disruption</option><option value="delay">Delay</option><option value="cancellation">Cancellation</option><option value="denied boarding">Denied boarding</option><option value="other">Other</option></select></div>
    <div className="field"><label htmlFor="scheduled">Scheduled departure <span>· optional</span></label><input id="scheduled" type="time" value={form.scheduled_time ?? ''} onChange={e => update('scheduled_time', e.target.value)}/></div>
    <div className="field"><label htmlFor="actual">Actual departure <span>· optional</span></label><input id="actual" type="time" value={form.actual_time ?? ''} onChange={e => update('actual_time', e.target.value)}/></div>
    <div className="field full"><label htmlFor="complaint">What happened? <span>· required</span></label><textarea id="complaint" required maxLength={10_000} value={form.complaint} onChange={e => update('complaint', e.target.value)} placeholder="Describe the disruption, what the airline told you, and what outcome you are seeking…"/><small>{form.complaint.length.toLocaleString()} / 10,000 characters. Avoid including sensitive payment details.</small></div>
    </div><div className="form-footer"><small><ShieldCheck size={13} style={{verticalAlign:'middle',marginRight:5}}/> Claim is stored for processing</small><button className="button-primary" type="submit" disabled={busy}>{busy ? <><LoaderCircle className="animate-spin" size={15}/> Sending…</> : <>Submit claim <ArrowRight size={15}/></>}</button></div></form>
    <aside className="panel side-note"><h3>Before you submit</h3><div className="side-item"><Info size={16}/><span>Your description is the required field. Flight number and times help add context when available.</span></div><div className="side-item"><FileText size={16}/><span>Document uploads are not supported by this API yet. Keep relevant records available for a human reviewer.</span></div><div className="side-item"><CircleHelp size={16}/><span>The current workflow is demo mode and provides preliminary triage only.</span></div></aside></div></div>
}
