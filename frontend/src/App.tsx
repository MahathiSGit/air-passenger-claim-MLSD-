import { useState } from 'react'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { Activity, ArrowRight, Menu, Plane, ShieldCheck, X } from 'lucide-react'
import { HomePage } from './pages/HomePage'
import { SubmitPage } from './pages/SubmitPage'
import { TrackPage } from './pages/TrackPage'
import { ResultPage } from './pages/ResultPage'
import { AdminPage } from './pages/AdminPage'

function Brand() {
  return <Link to="/" className="brand" aria-label="AirClaim home"><span className="brand-mark"><Plane size={19} fill="currentColor" /></span><span>air<span className="brand-light">claim</span></span></Link>
}

function Header() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)
  return <header className="topbar"><div className="nav-wrap"><Brand /><button className="mobile-menu" onClick={() => setOpen(!open)} aria-label="Toggle navigation">{open ? <X /> : <Menu />}</button><nav className={open ? 'nav-links nav-open' : 'nav-links'}><NavLink onClick={close} to="/" end>Overview</NavLink><NavLink onClick={close} to="/track">Track a claim</NavLink><NavLink onClick={close} to="/admin"><Activity size={15} /> Operations</NavLink><Link onClick={close} className="nav-cta" to="/submit">Start a claim <ArrowRight size={15} /></Link></nav></div></header>
}

export default function App() {
  return <div className="app-shell"><Header /><main><Routes><Route path="/" element={<HomePage />} /><Route path="/submit" element={<SubmitPage />} /><Route path="/track" element={<TrackPage />} /><Route path="/result/:claimId" element={<ResultPage />} /><Route path="/admin" element={<AdminPage />} /><Route path="*" element={<HomePage />} /></Routes></main><footer className="footer"><div className="footer-inner"><Brand /><span><ShieldCheck size={15} /> Private by design · Human-reviewed recommendations</span><span>© 2026 AirClaim</span></div></footer></div>
}
