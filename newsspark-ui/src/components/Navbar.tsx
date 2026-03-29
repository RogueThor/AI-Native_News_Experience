import { useNavigate, useLocation } from 'react-router-dom'
import { useSession } from '../App'

export default function Navbar() {
  const { user, setUser } = useSession()
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path ? 'active' : ''

  async function handleLogout() {
    try { await fetch('/logout') } catch {}
    setUser(null)
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <a className="nav-brand" onClick={() => navigate('/feed')} style={{ cursor: 'pointer' }}>
        ⚡ News<span>Spark</span>
      </a>
      <div className="nav-center">
        <button className={`nav-link ${isActive('/feed')}`} onClick={() => navigate('/feed')}>Feed</button>
        <button className={`nav-link ${isActive('/briefing')}`} onClick={() => navigate('/briefing')}>Briefings</button>
        <button className={`nav-link ${isActive('/chat')}`} onClick={() => navigate('/chat')}>💬 Catch Me Up</button>
      </div>
      <div className="nav-right">
        {user && (
          <>
            <div className="pill-status">
              <span className="pill-dot" />
              Live Feed
            </div>
            <div className="nav-user">
              <div className="nav-avatar">{user.avatar}</div>
              <span>{user.name}</span>
            </div>
          </>
        )}
        <button className="btn-logout" onClick={handleLogout}>Logout</button>
      </div>
    </nav>
  )
}
