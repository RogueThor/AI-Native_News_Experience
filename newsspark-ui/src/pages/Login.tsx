import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession, useAppToast } from '../App'
import Spinner from '../components/Spinner'

const PERSONAS = [
  { role: 'investor',        avatar: '💼', name: 'Arjun Mehta',  label: 'Investor',        interests: 'Markets · Business · Policy' },
  { role: 'student',         avatar: '🎓', name: 'Priya Sharma', label: 'Student',          interests: 'Education · Tech · Health' },
  { role: 'founder',         avatar: '🚀', name: 'Kiran Rao',    label: 'Founder',          interests: 'Business · Startups · Tech' },
  { role: 'general',         avatar: '📰', name: 'Rahul Verma',  label: 'General Reader',   interests: 'Politics · Crime · Health' },
  { role: 'sports_fan',      avatar: '🏏', name: 'Vikas Reddy',  label: 'Sports Fan',       interests: 'Cricket · Sports · IPL' },
  { role: 'tech_enthusiast', avatar: '💻', name: 'Sneha Iyer',   label: 'Tech Enthusiast',  interests: 'Technology · AI · Startups' },
  { role: 'job_seeker',      avatar: '🔍', name: 'Amit Gupta',   label: 'Job Seeker',       interests: 'Jobs · Education · Business' },
  { role: 'homemaker',       avatar: '🏠', name: 'Deepa Nair',   label: 'Homemaker',        interests: 'Health · Entertainment · Crime' },
]

export default function Login() {
  const { setUser } = useSession()
  const { addToast } = useAppToast()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  async function doLogin(persona: typeof PERSONAS[0]) {
    setLoading(true)
    const fd = new FormData()
    fd.append('role', persona.role)
    try {
      const resp = await fetch('/login', { 
        method: 'POST', 
        body: fd, 
        headers: { 'Accept': 'application/json' }
      })
      
      if (resp.ok) {
        const userData = await resp.json()
        setUser(userData)
        navigate('/feed')
      } else {
        throw new Error('Login failed')
      }
    } catch (e: any) {
      addToast('Login failed. Please ensure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <span className="logo-icon">⚡</span>
          <div className="logo-name">News<span style={{ color: 'var(--accent)' }}>Spark</span></div>
          <div className="logo-tagline">AI-Native Indian News Platform</div>
        </div>

        <h2 className="login-heading">Choose Your Profile</h2>
        <p className="login-subtext">Select a demo profile to explore NewsSpark</p>

        <div className="profile-grid" style={{ pointerEvents: loading ? 'none' : 'auto' }}>
          {PERSONAS.map(p => (
            <div
              key={p.role}
              className="profile-card"
              onClick={() => doLogin(p)}
              role="button"
              tabIndex={0}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') doLogin(p) }}
              aria-label={p.label}
            >
              <span className="profile-avatar">{p.avatar}</span>
              <span className="profile-name">{p.name}</span>
              <span className="profile-role">{p.label}</span>
              <span className="profile-interests">{p.interests}</span>
            </div>
          ))}
        </div>

        {loading && (
          <div className="login-loading">
            <Spinner center />
            <p>Signing you in…</p>
          </div>
        )}
      </div>
    </div>
  )
}
