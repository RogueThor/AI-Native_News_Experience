import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Spinner from '../components/Spinner'
import { fetchArc } from '../api'
import type { ArcData } from '../api'
import { useAppToast } from '../App'

export default function Arc() {
  const { topic } = useParams<{ topic: string }>()
  const navigate = useNavigate()
  const { addToast } = useAppToast()
  const [arc, setArc] = useState<ArcData | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!topic) return
    setLoading(true)
    fetchArc(topic)
      .then(data => {
        if (data.arc) setArc(data.arc)
        else setNotFound(true)
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [topic])

  async function refreshArc() {
    addToast('Refreshing story arc…')
    try {
      const data = await fetchArc(topic!, true)
      if (data.arc) {
        setArc(data.arc)
        addToast('Arc refreshed!')
      }
    } catch {
      addToast('Could not refresh — try again later.')
    }
  }

  const dotColor = (s: string) => s === 'positive' ? 'var(--positive)' : s === 'negative' ? 'var(--negative)' : 'var(--accent)'

  if (loading) return <div className="page-wrapper"><Spinner center /></div>

  if (notFound || !arc) return (
    <div className="page-wrapper">
      <div className="arc-empty">
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
        <h3 style={{ fontSize: '1.1rem', color: 'var(--text-secondary)' }}>No arc data found for "{topic}"</h3>
        <p style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>More articles are needed to build a story arc for this topic.</p>
        <button className="btn btn-primary" style={{ marginTop: '1.5rem' }} onClick={() => navigate('/feed')}>← Back to Feed</button>
      </div>
    </div>
  )

  return (
    <div className="page-wrapper">
      <div className="arc-page">
        <div className="arc-page-header">
          <h1>📖 {arc.topic_name}</h1>
          <p>Story arc · Last updated: {arc.last_updated?.substring(0, 10) || 'N/A'}</p>
        </div>

        <div className="arc-layout">
          {/* Timeline */}
          <div className="arc-panel">
            <h3>📅 Timeline</h3>
            {arc.timeline && arc.timeline.length > 0 ? (
              <div className="timeline">
                {arc.timeline.map((item, i) => (
                  <div key={i} className="tl-item">
                    <div className="tl-dot" style={{ background: dotColor(item.sentiment) }} />
                    <div className="tl-date">{item.date}</div>
                    <div className="tl-headline">{item.headline}</div>
                    <span className={`tag ${item.sentiment}`}>{item.sentiment}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No timeline data yet.</p>
            )}
          </div>

          {/* Middle: Key players + Sentiment */}
          <div>
            <div className="arc-panel" style={{ marginBottom: '1.5rem' }}>
              <h3>👥 Key Players</h3>
              {arc.key_players && arc.key_players.length > 0 ? (
                <div className="player-cloud">
                  {arc.key_players.map((p, i) => <span key={i} className="player-badge">{p}</span>)}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No key players identified.</p>
              )}
            </div>

            <div className="arc-panel">
              <h3>📊 Sentiment Trend</h3>
              {arc.sentiment_trend && arc.sentiment_trend.length > 0 ? (
                <div className="sent-chart">
                  {arc.sentiment_trend.map((pt, i) => {
                    const pct = Math.round(((pt.score + 1) / 2) * 100)
                    const cls = pt.score > 0 ? 'positive' : pt.score < 0 ? 'negative' : 'neutral'
                    return (
                      <div key={i} className="sent-row">
                        <span className="sent-lbl">{pt.date.slice(-5)}</span>
                        <div className="sent-track">
                          <div className={`sent-fill ${cls}`} style={{ width: `${pct}%` }} />
                        </div>
                        <span className={`tag ${cls}`} style={{ fontSize: '0.65rem' }}>{cls}</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No sentiment data available.</p>
              )}
            </div>
          </div>

          {/* Right: What's next + Deep dive */}
          <div>
            <div className="arc-panel">
              <h3>🔭 What's Next</h3>
              <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {arc.what_to_watch_next || 'Check back after more news is collected.'}
              </p>
            </div>

            <div className="watch-next-card">
              <h3>📌 Deep Dive</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 500, fontStyle: 'italic' }}>
                Want a full briefing on this topic?
              </p>
              <button
                className="btn btn-primary"
                style={{ marginTop: '0.75rem' }}
                onClick={() => navigate(`/briefing?topic=${arc._id}`)}
              >
                Get Briefing →
              </button>
            </div>

            <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
              <button className="btn btn-outline" onClick={refreshArc}>🔄 Refresh Arc</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
