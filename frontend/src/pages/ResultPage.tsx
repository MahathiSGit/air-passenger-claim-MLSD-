import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, BadgeCheck, BookOpen, CircleAlert, FileSearch, ShieldCheck } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { claimsApi, getApiError, type ClaimResultResponse, type ClaimStatusResponse } from '../api'

const recommendationText: Record<string, string> = {
  pay_as_computed: 'Payment may be considered',
  request_further_evidence: 'More information may be needed',
  decline: 'The current assessment suggests no payment',
  escalate_to_human: 'Human review recommended',
}

export function ResultPage() {
  const { claimId = '' } = useParams()
  const [result, setResult] = useState<ClaimResultResponse | null>(null)
  const [status, setStatus] = useState<ClaimStatusResponse | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const current = await claimsApi.status(claimId)
      setStatus(current)
      if (current.status === 'completed') {
        const output = await claimsApi.result(claimId)
        setResult(output)
        setError('')
      } else if (current.status === 'failed') {
        setResult(null)
        setError(current.failure_message || 'Claim processing failed.')
      }
    } catch (cause) { setError(getApiError(cause)) }
  }, [claimId])

  useEffect(() => { void load() }, [load])
  useEffect(() => {
    if (!status || !['pending', 'processing'].includes(status.status)) return
    const timer = window.setInterval(() => { void load() }, 3500)
    return () => window.clearInterval(timer)
  }, [load, status?.status])

  const workflow = result?.result
  const entitlement = workflow?.entitlement
  const research = workflow?.regulation_research

  return <div className="page result-page"><div className="page-heading"><Link className="text-link" to="/track"><ArrowLeft size={14}/> Back to tracking</Link><span className="eyebrow" style={{display:'flex',marginTop:16}}>Claim assessment</span><h1>Review your result</h1><p>Claim <span className="mono">{claimId}</span></p></div>
    {!workflow && !error && <section className="result-card"><div style={{display:'flex',alignItems:'center',gap:11}}><span className="spinner"/><div><strong style={{fontSize:13,color:'#264b69'}}>Your claim is {status?.status ?? 'loading'}</strong><p className="muted">This page checks for updates automatically.</p></div></div></section>}
    {error && <div className="api-error" role="alert">{error}</div>}
    {workflow && entitlement && <>
      {workflow.mode === 'demo' && <div className="demo-note"><strong>Demo mode · preliminary triage.</strong> {workflow.note} This is not a legally binding decision.</div>}
      <section className="result-card"><div className="result-top"><div><span className="eyebrow">Recommendation</span><div className={`recommendation ${entitlement.recommendation}`}><h2>{recommendationText[entitlement.recommendation] || entitlement.recommendation.replaceAll('_',' ')}</h2><p>{entitlement.rationale}</p>{entitlement.compensation_amount != null && <p style={{marginTop:8,fontWeight:700}}>Indicative amount: {entitlement.currency || ''} {entitlement.compensation_amount}</p>}</div></div><span className="status-pill completed"><i className="status-dot"/> completed</span></div><div className="muted">Claim ID: <span className="mono">{result.claim_id}</span></div>
        <div className="result-section"><h3><BadgeCheck size={15}/> Verification</h3><p>{workflow.verification.supported ? 'The workflow marked this assessment as supported by its available evidence.' : 'The workflow identified verification flags or unresolved uncertainty.'}</p>{workflow.verification.flags?.length > 0 && <ul>{workflow.verification.flags.map((flag, i) => <li key={i}>{flag}</li>)}</ul>}</div>
        {(workflow.claim_analysis.missing_information?.length || entitlement.uncertainties?.length || research?.evidence_gaps?.length) ? <div className="result-section"><h3><CircleAlert size={15}/> Uncertainties and missing information</h3><ul>{[...(workflow.claim_analysis.missing_information || []), ...(entitlement.uncertainties || []), ...(research?.evidence_gaps || [])].filter((value, i, all) => all.indexOf(value) === i).map((item, i) => <li key={i}>{item}</li>)}</ul></div> : null}
      </section>
      <section className="result-card"><div className="result-section" style={{marginTop:0}}><h3><FileSearch size={15}/> Retrieved regulatory passages</h3>{research?.relevant_provisions?.length ? research.relevant_provisions.map((provision, i) => <article className="citation-item" key={`${provision.citation || provision.source || 'source'}-${i}`}><strong>{provision.citation || provision.source || 'Source reference unavailable'}</strong><div className="citation-meta" style={{marginTop:8}}>{provision.source && <span>{provision.source}</span>}{provision.page != null && <span>Page {provision.page}</span>}{provision.section && <span>{provision.section}</span>}</div>{provision.text && <p>{provision.text}</p>}</article>) : <p>No retrieved passages were included in the workflow result.</p>}</div>
        {research?.conditions?.length ? <div className="result-section"><h3><BookOpen size={15}/> Conditions noted</h3><ul>{research.conditions.map((condition, i) => <li key={i}>{condition}</li>)}</ul></div> : null}
        <div className="disclaimer" style={{marginBottom:0}}><ShieldCheck size={16}/><span><strong>Human review is required.</strong> This demo assessment is preliminary and does not determine legal eligibility or authorize compensation.</span></div>
      </section>
    </>}
  </div>
}
