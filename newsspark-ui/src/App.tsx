import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Feed from './pages/Feed'
import Chat from './pages/Chat'
import Briefing from './pages/Briefing'
import Arc from './pages/Arc'
import Navbar from './components/Navbar'
import Toast, { useToast } from './components/Toast'
import Spinner from './components/Spinner'
import { fetchCurrentUser } from './api'
import './index.css'

// ── Session context ───────────────────────────────────────────────────────────

export interface SessionUser {
  _id: string
  name: string
  avatar: string
  role: string
  language_pref?: string
}

interface SessionCtx {
  user: SessionUser | null
  setUser: (u: SessionUser | null) => void
}

export const SessionContext = createContext<SessionCtx>({ user: null, setUser: () => {} })
export const useSession = () => useContext(SessionContext)

// ── Toast context ─────────────────────────────────────────────────────────────

interface ToastCtx { addToast: (msg: string) => void }
export const ToastContext = createContext<ToastCtx>({ addToast: () => {} })
export const useAppToast = () => useContext(ToastContext)

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [loading, setLoading] = useState(true)
  const { toasts, addToast, removeToast } = useToast()

  const addToastCb = useCallback((msg: string) => addToast(msg), [addToast])

  useEffect(() => {
    async function init() {
      try {
        const u = await fetchCurrentUser()
        if (u) setUser(u as SessionUser)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  if (loading) return <Spinner center />


  return (
    <SessionContext.Provider value={{ user, setUser }}>
      <ToastContext.Provider value={{ addToast: addToastCb }}>
        <BrowserRouter>
          {user && <Navbar />}
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/feed"     element={user ? <Feed />     : <Navigate to="/login" />} />
            <Route path="/chat"     element={user ? <Chat />     : <Navigate to="/login" />} />
            <Route path="/briefing" element={user ? <Briefing /> : <Navigate to="/login" />} />
            <Route path="/arc/:topic" element={user ? <Arc />    : <Navigate to="/login" />} />
            <Route path="*" element={<Navigate to={user ? '/feed' : '/login'} />} />
          </Routes>
          <Toast toasts={toasts} onRemove={removeToast} />
        </BrowserRouter>
      </ToastContext.Provider>
    </SessionContext.Provider>
  )
}
