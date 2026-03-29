import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Spinner from '../components/Spinner'
import { fetchBriefing, askBriefingQuestion } from '../api'

const TOPICS = [
  { key: 'markets', icon: '📈', label: 'Markets' },
  { key: 'budget',  icon: '💰', label: 'Budget' },
  { key: 'startup', icon: '🚀', label: 'Startups' },
  { key: 'policy',  icon: '📋', label: 'Policy' },
  { key: 'rbi',     icon: '🏦', label: 'RBI' },
  { key: 'other',   icon: '📰', label: 'Other' },
]

interface Bubble { from: 'user' | 'assistant'; text: string }

export default function Briefing() {
  const location = useLocation()
  const navigate = useNavigate()
  const [topic, setTopic] = useState('markets')
  const [briefText, setBriefText] = useState('')
  const [loading, setLoading] = useState(false)

  // Audio
  const [playing, setPlaying] = useState(false)
  const synthRef = useRef(window.speechSynthesis)

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [qaInput, setQaInput] = useState('')
  const [bubbles, setBubbles] = useState<Bubble[]>([
    { from: 'assistant', text: '👋 I\'ve analyzed this dossier. Ask me anything!' }
  ])
  const [qaSending, setQaSending] = useState(false)
  const messagesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Pick topic from query string
    const params = new URLSearchParams(location.search)
    const t = params.get('topic')
    if (t && t !== topic) setTopic(t)
  }, [location.search])

  useEffect(() => { 
    load(topic)
    navigate(`/briefing?topic=${topic}`, { replace: true })
  }, [topic])

  async function load(t: string) {
    setLoading(true)
    setBriefText('')
    stopAudio()
    try {
      const text = await fetchBriefing(t)
      setBriefText(text)
    } catch (e: any) {
      setBriefText('Error loading briefing: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  function toggleAudio() {
    if (playing) {
      stopAudio()
    } else {
      const u = new SpeechSynthesisUtterance(briefText)
      u.onend = stopAudio
      synthRef.current.speak(u)
      setPlaying(true)
    }
  }

  function stopAudio() {
    synthRef.current.cancel()
    setPlaying(false)
  }

  async function sendQuestion() {
    if (!qaInput.trim() || qaSending) return
    const q = qaInput.trim()
    setQaInput('')
    setBubbles(prev => [...prev, { from: 'user', text: q }])
    setQaSending(true)
    setBubbles(prev => [...prev, { from: 'assistant', text: 'Thinking…' }])
    setTimeout(() => messagesRef.current?.scrollTo(0, messagesRef.current.scrollHeight), 50)
    try {
      const answer = await askBriefingQuestion(topic, q)
      setBubbles(prev => {
        const arr = [...prev]
        arr[arr.length - 1] = { from: 'assistant', text: answer }
        return arr
      })
    } catch (e: any) {
      setBubbles(prev => {
        const arr = [...prev]
        arr[arr.length - 1] = { from: 'assistant', text: 'Error: ' + e.message }
        return arr
      })
    } finally {
      setQaSending(false)
      setTimeout(() => messagesRef.current?.scrollTo(0, messagesRef.current.scrollHeight), 50)
    }
  }

  const dateLabel = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })

  return (
    <div className="page-wrapper">
      <div className="briefing-page">
        <div className="briefing-header">
          <h1>📋 Executive Briefings</h1>
          <p>AI-curated sector intelligence reports for the Indian market</p>
        </div>

        {/* Topic picker */}
        <div className="topic-bar">
          {TOPICS.map(t => (
            <div
              key={t.key}
              className={`topic-card ${topic === t.key ? 'active' : ''}`}
              onClick={() => setTopic(t.key)}
            >
              <span className="icon">{t.icon}</span>
              <span className="label">{t.label}</span>
            </div>
          ))}
        </div>

        {/* Dossier */}
        <div className="dossier-body">
          {loading && <Spinner center />}
          {!loading && (
            <>
              <div className="dossier-header">
                <div className="dossier-meta">{dateLabel} · AI Intelligence Report</div>
                <h2 className="dossier-title">
                  {TOPICS.find(t => t.key === topic)?.icon} {topic.charAt(0).toUpperCase() + topic.slice(1)} Briefing
                </h2>
              </div>

              {briefText && (
                <div className="briefing-actions">
                  <button className={`btn-audio ${playing ? 'playing' : ''}`} onClick={toggleAudio}>
                    <span>{playing ? '⏹' : '🔊'}</span>
                    <span>{playing ? 'Stop Audio' : 'Play Audio Briefing'}</span>
                  </button>
                </div>
              )}

              <div className="briefing-text">
                {briefText || (
                  <div className="empty-state">
                    <div className="icon">📋</div>
                    <h3>Select a topic above</h3>
                    <p>AI will analyze the latest data to prepare your executive summary.</p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Floating chat button */}
      <button className="chat-fab" onClick={() => setDrawerOpen(true)} aria-label="Open AI Discussion">
        💬
      </button>

      {/* Slide-out Q&A drawer */}
      <div className={`chat-drawer ${drawerOpen ? 'open' : ''}`}>
        <div className="drawer-header">
          <h3>AI Discussion</h3>
          <button className="btn btn-outline" style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem' }} onClick={() => setDrawerOpen(false)}>✕</button>
        </div>
        <div className="drawer-messages" ref={messagesRef}>
          {bubbles.map((b, i) => (
            <div key={i} className={`chat-bubble ${b.from}`}>{b.text}</div>
          ))}
        </div>
        <div className="drawer-input">
          <input
            type="text"
            value={qaInput}
            onChange={e => setQaInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') sendQuestion() }}
            placeholder="Type your question…"
            disabled={qaSending}
          />
          <button className="btn btn-primary" onClick={sendQuestion} disabled={qaSending || !qaInput.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
