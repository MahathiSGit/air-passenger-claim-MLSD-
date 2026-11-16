import { ArrowDown, ArrowRight, BookOpenCheck, CheckCircle2, ClipboardCheck, FileSearch, LockKeyhole, Plane, Scale, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

export function HomePage() {
  return <>
    <section className="page hero">
      <div>
        <span className="eyebrow"><i className="eyebrow-dot" /> Air passenger compensation assistant</span>
        <h1>Your journey deserves a <em>fair review.</em></h1>
        <p className="hero-copy">A clearer way to organize a flight disruption claim. AirClaim reviews the details you provide alongside relevant passenger-rights material, then shows its reasoning and sources.</p>
        <div className="hero-actions"><Link className="button-primary" to="/submit">Submit a claim <ArrowRight size={16} /></Link><Link className="text-link" to="/track">Already submitted? Track it <ArrowDown size={14} /></Link></div>
        <div className="trustline"><CheckCircle2 size={15} /> Transparent sources <span>·</span> Human review required</div>
      </div>
      <div className="hero-art" aria-label="Illustration of a flight route and regulatory review">
        <div className="plane-scene"><div className="plane-disc"><Plane size={92} strokeWidth={1.1} /></div>
          <div className="float-card route"><span className="mini-label">Flight overview</span><strong>AI 245 · DEL → BOM</strong><small>Disruption details organized</small><div className="route-path"><span>DEL</span><i /><span>BOM</span></div></div>
          <div className="float-card evidence"><div className="evidence-top"><BookOpenCheck size={16} /><strong>Source-backed review</strong></div><small>Relevant passages are included</small><span className="evidence-tag">Citations attached</span></div>
        </div>
      </div>
    </section>
    <section className="section"><div className="page"><div className="section-head"><span className="eyebrow">A simple process</span><h2>From disruption to a clearer next step</h2><p>Share what happened, let the system organize the available information, then review the result and its sources.</p></div><div className="steps-grid">
      {[['01','Tell us what happened','Add your flight details and describe the disruption in your own words.',<ClipboardCheck size={20}/>],['02','Review relevant material','The service retrieves matching passages from its configured passenger-rights documents.',<FileSearch size={20}/>],['03','See a transparent assessment','Read the suggested next step, supporting citations, and any gaps that need attention.',<Scale size={20}/>]].map(([num,title,copy,icon])=><article className="step-card" key={String(num)}><span className="step-num">{num} / PROCESS</span><div className="step-icon">{icon}</div><h3>{title}</h3><p>{copy}</p></article>)}
    </div></div></section>
    <section className="section feature-section"><div className="page"><div className="section-head"><span className="eyebrow">Built for clarity</span><h2>Useful context, with receipts</h2><p>AirClaim is designed to make the review process easier to understand, not to make a binding decision.</p></div><div className="features-grid">
      {[['Grounded in source text','Relevant retrieved passages and available page references are shown alongside the assessment.',<BookOpenCheck size={20}/>],['Structured claim review','The workflow organizes reported facts, recommendation, uncertainties, and verification findings.',<Sparkles size={20}/>],['Your claim stays traceable','A unique claim ID lets you check processing progress and return to the completed result.',<LockKeyhole size={20}/>]].map(([title,copy,icon])=><article className="feature-card" key={String(title)}><div className="feature-icon">{icon}</div><h3>{title}</h3><p>{copy}</p></article>)}
    </div><div className="disclaimer"><LockKeyhole size={17}/><span><strong>Preliminary triage only.</strong> AirClaim uses the configured demo workflow. Its recommendation is not legal advice, a final eligibility decision, or an authorization to pay compensation. A qualified human reviewer must assess the claim.</span></div></div></section>
  </>
}
