import { useEffect, useRef, useState } from 'react'
import { useSession } from '../App'
import Spinner from '../components/Spinner'
import type { ChatMessage } from '../api'

const CHIPS = [
  { label: '💰 Budget 2026',      msg: 'Catch me up on Budget 2026' },
  { label: '🏏 IPL 2026',         msg: 'Latest IPL 2026 updates' },
  { label: '🚀 Tech Startups',    msg: 'What is happening in Indian tech startups?' },
  { label: '📈 Stock Market',     msg: 'India stock market this week' },
  { label: '🗳️ Politics',         msg: 'Indian politics latest news' },
  { label: '🏢 Reliance',         msg: 'Reliance Industries latest news' },
]

interface MsgItem {
  from: 'user' | 'bot' | 'error' | 'thinking'
  text?: string
  data?: ChatMessage
  id: number
}

export default function Chat() {
  const { user } = useSession()
  const [msgs, setMsgs] = useState<MsgItem[]>([])
  const [input, setInput] = useState('')
  const [waiting, setWaiting] = useState(false)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelay = useRef(1000)
  const historyRef = useRef<HTMLDivElement>(null)
  const counter = useRef(0)

  function scrollBottom() { historyRef.current?.scrollTo(0, historyRef.current.scrollHeight) }

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws/chat/${user!._id}`)
    wsRef.current = ws

    ws.onopen = () => { setWsStatus('connected'); reconnectDelay.current = 1000 }
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        setMsgs(prev => prev.filter(m => m.from !== 'thinking'))
        setWaiting(false)
        if (msg.type === 'response') {
          setMsgs(prev => [...prev, { from: 'bot', data: msg.data, id: ++counter.current }])
        } else if (msg.type === 'thinking') {
          setMsgs(prev => [...prev, { from: 'thinking', text: msg.message, id: ++counter.current }])
        } else if (msg.type === 'error') {
          setMsgs(prev => [...prev, { from: 'error', text: msg.message, id: ++counter.current }])
        }
      } catch {}
      setTimeout(scrollBottom, 50)
    }
    ws.onclose = () => {
      setWsStatus('disconnected')
      reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
      setTimeout(connect, reconnectDelay.current)
    }
    ws.onerror = () => ws.close()
  }

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [])

  function sendMessage(text?: string) {
    const msg = text || input.trim()
    if (!msg || waiting) return
    setInput('')
    setWaiting(true)
    setMsgs(prev => [...prev, { from: 'user', text: msg, id: ++counter.current }])
    setTimeout(scrollBottom, 50)

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: msg }))
      setMsgs(prev => [...prev, { from: 'thinking', text: 'Searching news sources…', id: ++counter.current }])
    } else {
      // REST fallback
      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, user_id: user!._id }),
      })
        .then(r => r.json())
        .then(data => {
          setMsgs(prev => prev.filter(m => m.from !== 'thinking'))
          setMsgs(prev => [...prev, { from: 'bot', data, id: ++counter.current }])
          setWaiting(false)
          setTimeout(scrollBottom, 50)
        })
        .catch(e => {
          setMsgs(prev => prev.filter(m => m.from !== 'thinking'))
          setMsgs(prev => [...prev, { from: 'error', text: e.message, id: ++counter.current }])
          setWaiting(false)
        })
    }
  }

  const sentDot = (s: string) => s === 'positive' ? 'positive' : s === 'negative' ? 'negative' : 'neutral'

  return (
    <div className="page-wrapper">
      <div className="chat-page">
        <div className="chat-page-header">
          <h1>💬 Catch Me Up</h1>
          <p>Ask about any Indian news topic. AI searches real-time + stored articles.</p>
        </div>

        {/* Quick chips */}
        <div className="chips">
          {CHIPS.map(c => (
            <button key={c.label} className="chip" onClick={() => sendMessage(c.msg)}>{c.label}</button>
          ))}
        </div>

        {/* WS status */}
        <div className="ws-status">
          {wsStatus === 'connected' && <span className="ws-connected">● Connected</span>}
          {wsStatus === 'connecting' && <span>Connecting…</span>}
          {wsStatus === 'disconnected' && <span className="ws-disconnected">● Disconnected — reconnecting…</span>}
        </div>

        {/* Chat history */}
        <div className="chat-history" ref={historyRef}>
          {msgs.length === 0 && (
            <div className="chat-welcome">Ask me anything about Indian news! 🇮🇳</div>
          )}

          {msgs.map(m => {
            if (m.from === 'user') return (
              <div key={m.id} className="user-bubble">{m.text}</div>
            )
            if (m.from === 'thinking') return (
              <div key={m.id} className="thinking">
                <div className="dot-anim"><span/><span/><span/></div>
                {m.text}
              </div>
            )
            if (m.from === 'error') return (
              <div key={m.id} style={{ color: 'var(--negative)', fontSize: '0.85rem', padding: '0.5rem' }}>
                ⚠️ {m.text}
              </div>
            )
            // Bot response
            const d = m.data!
            return (
              <div key={m.id} className="bot-response">
                <div className="response-topic">📰 {d.topic || 'News Update'}</div>
                {d.summary && <div className="response-summary">{d.summary}</div>}
                {d.timeline && d.timeline.length > 0 && (
                  <div className="timeline-list">
                    {d.timeline.map((t, i) => (
                      <div key={i} className="timeline-item">
                        <span className={`s-dot ${sentDot(t.sentiment)}`} />
                        <span className="t-date">{t.date}</span>
                        <span className="t-line">{t.headline}</span>
                      </div>
                    ))}
                  </div>
                )}
                {d.sources && d.sources.length > 0 && (
                  <div className="response-sources">
                    Sources: {d.sources.map((s, i) => <span key={i} className="source-tag">{s}</span>)}
                  </div>
                )}
                {d._meta && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                    📚 {d._meta.chroma_count} stored · {d._meta.used_live_search ? '🌐 Live search used' : '✅ From stored'}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Input bar */}
        <div className="chat-input-bar">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') sendMessage() }}
            placeholder="e.g. What happened with Adani this week?"
            maxLength={300}
            disabled={waiting}
          />
          <button className="btn btn-primary" onClick={() => sendMessage()} disabled={waiting || !input.trim()}>
            {waiting ? <Spinner /> : 'Send ➤'}
          </button>
        </div>
      </div>
    </div>
  )
}
