import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession, useAppToast } from '../App'
import { fetchFeed, fetchTranslation, trackInteraction } from '../api'
import type { Article } from '../api'
import Modal from '../components/Modal'
import Spinner from '../components/Spinner'
import AIReporter from '../features/AIReporter'

const CATEGORIES = [
  { key: 'top',           label: '🌟 Top Stories' },
  { key: 'business',      label: '💼 Business' },
  { key: 'technology',    label: '💻 Technology' },
  { key: 'politics',      label: '🏛️ Politics' },
  { key: 'sports',        label: '🏏 Sports' },
  { key: 'entertainment', label: '🎬 Entertainment' },
  { key: 'science',       label: '🔬 Science' },
]

const CAT_ICON: Record<string, string> = {
  markets: '📈', budget: '💰', startup: '🚀',
  policy: '📋', rbi: '🏦', other: '📰',
  business: '💼', technology: '💻', politics: '🏛️',
  sports: '🏏', entertainment: '🎬', science: '🔬',
}

const DEFAULT_IMAGES = [
  'https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=800&q=80',
  'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80',
  'https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80',
  'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?w=800&q=80',
  'https://images.unsplash.com/photo-1557428894-e0c1fce9bb71?w=800&q=80',
  'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80'
]

function getPlaceholderImage(title: string) {
  let hash = 0;
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash);
  }
  return DEFAULT_IMAGES[Math.abs(hash) % DEFAULT_IMAGES.length];
}

function stripHtml(html: string) {
  const d = document.createElement('div'); d.innerHTML = html; return d.textContent || ''
}

export default function Feed() {
  const { user } = useSession()
  const { addToast } = useAppToast()
  const navigate = useNavigate()

  const [articles, setArticles] = useState<Article[]>([])
  const [category, setCategory] = useState('top')
  const [loading, setLoading] = useState(true)

  // Translation modal
  const [transOpen, setTransOpen] = useState(false)
  const [transTitle, setTransTitle] = useState('')
  const [transText, setTransText] = useState<string | null>(null)
  const [transLoading, setTransLoading] = useState(false)

  // AI Reporter modal
  const [reporterArticle, setReporterArticle] = useState<Article | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelay = useRef(1000)

  // ── Load feed ──────────────────────────────────────────────────────────────
  const load = useCallback(async (cat: string) => {
    setLoading(true)
    try {
      const data = await fetchFeed(cat)
      setArticles(data)
    } catch (e: any) {
      addToast('Could not load feed')
    } finally {
      setLoading(false)
    }
  }, [addToast])

  useEffect(() => { load(category) }, [category])

  // ── WebSocket ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!user) return
    function connect() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws/feed/${user!._id}`)
      wsRef.current = ws
      ws.onopen = () => { reconnectDelay.current = 1000 }
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'new_articles' && msg.articles?.length) {
            setArticles(prev => [...msg.articles, ...prev])
            addToast(`🔔 ${msg.count} new articles added`)
          }
        } catch {}
      }
      ws.onclose = () => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
        setTimeout(connect, reconnectDelay.current)
      }
      ws.onerror = () => ws.close()
    }
    connect()
    return () => { wsRef.current?.close() }
  }, [user])

  // ── Translation ────────────────────────────────────────────────────────────
  async function openTranslation(art: Article, lang: 'tamil' | 'hindi') {
    setTransTitle(lang === 'tamil' ? 'தமிழ் மொழிபெயர்ப்பு' : 'हिंदी अनुवाद')
    setTransText(null)
    setTransLoading(true)
    setTransOpen(true)
    try {
      const text = await fetchTranslation(art._id, lang)
      setTransText(text)
    } catch {
      setTransText('Translation failed. Please try again.')
    } finally {
      setTransLoading(false)
    }
  }

  function openArticle(art: Article) {
    if (art._id) trackInteraction(art._id, 'read')
    if (art.url) window.open(art.url, '_blank', 'noopener')
  }

  // Filter out NewsData.io paywall messages from API fields
  const isPaywall = (s?: string) => !s ? true : /only available in/i.test(s)
  const cleanSentiment = (s?: string) => {
    if (!s || isPaywall(s)) return undefined
    return s
  }
  const cleanText = (s?: string) => {
    if (!s) return ''
    return isPaywall(s) ? '' : s
  }

  const sentimentCls = (s?: string) =>
    s === 'positive' ? 'positive' : s === 'negative' ? 'negative' : ''

  return (
    <div className="page-wrapper">
      {/* Hero */}
      <div className="hero">
        <div className="hero-eyebrow">AI-Powered · Vernacular · Real-Time</div>
        <h1>Your Personalised<br />Indian News Feed 🇮🇳</h1>
        <div className="hero-sub">
          <span>{user?.avatar}</span>
          <span>Curated for <strong>{user?.name}</strong></span>
        </div>
      </div>

      <div className="container">
        {/* Category tabs */}
        <div className="cat-tabs">
          {CATEGORIES.map(c => (
            <button
              key={c.key}
              className={`cat-tab ${category === c.key ? 'active' : ''}`}
              onClick={() => setCategory(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Two-column layout */}
        <div className="split-layout">
          {/* Article list */}
          <main>
            {loading && <Spinner center />}
            {!loading && articles.length === 0 && (
              <div className="empty-state">
                <div className="icon">🗞️</div>
                <h3>No articles yet</h3>
                <p>News is being fetched — check back in a moment.</p>
              </div>
            )}
            {!loading && (
              <div className="article-list">
                {articles.map(art => {
                  const icon = CAT_ICON[art.category || ''] || '📰'
                  const dateStr = art.published_at ? art.published_at.substring(0, 10) : ''
                  return (
                    <article key={art._id} className="article-item" onClick={() => openArticle(art)}>
                      {/* Thumbnail */}
                      <div className="article-thumb">
                        <img 
                          src={art.image_url || getPlaceholderImage(art.title)} 
                          alt={art.title} 
                          onError={(e) => { (e.target as HTMLImageElement).src = getPlaceholderImage(art.title + "1") }} 
                        />
                      </div>

                      <div className="article-content">
                        {/* Tags row */}
                        <div className="tag-row">
                          <span className="tag accent">{icon} {art.category || 'news'}</span>
                          {cleanSentiment(art.sentiment) && (
                            <span className={`tag ${sentimentCls(cleanSentiment(art.sentiment))}`}>{cleanSentiment(art.sentiment)}</span>
                          )}
                          {art.story_cluster_id && (
                            <a
                              className="tag"
                              href="#"
                              onClick={e => { e.stopPropagation(); e.preventDefault(); navigate(`/arc/${encodeURIComponent(art.story_cluster_id!)}`) }}
                            >
                              Story Arc →
                            </a>
                          )}
                        </div>

                        <h2 className="article-title">{art.title}</h2>

                        {/* Meta row */}
                        <div className="article-meta">
                          {dateStr && <><span>📅 {dateStr}</span><span className="meta-sep">·</span></>}
                          {art.source && <span>📰 {art.source}</span>}
                        </div>

                        <p className="article-desc">{stripHtml(cleanText(art.description) || cleanText(art.content) || '')}</p>

                        {/* Action pills */}
                        <div className="article-actions">
                          {art._id && (
                            <>
                              <button
                                className="pill-btn"
                                onClick={e => { e.stopPropagation(); openTranslation(art, 'tamil') }}
                                title="Tamil translation"
                              >த Tamil</button>
                              <button
                                className="pill-btn"
                                onClick={e => { e.stopPropagation(); openTranslation(art, 'hindi') }}
                                title="Hindi translation"
                              >हि Hindi</button>
                              <button
                                className="pill-btn reporter"
                                onClick={e => { e.stopPropagation(); setReporterArticle(art) }}
                                title="AI Reporter"
                              >🎙️ AI Reporter</button>
                            </>
                          )}
                          <a
                            className="read-more-link"
                            href={art.url}
                            target="_blank"
                            rel="noopener"
                            onClick={e => e.stopPropagation()}
                          >
                            Read More →
                          </a>
                        </div>
                      </div>
                    </article>
                  )
                })}
              </div>
            )}
          </main>

          {/* Sidebar */}
          <aside className="sidebar">
            {/* Quick links widget */}
            <div className="widget">
              <p className="widget-title">Quick Links</p>
              <div className="widget-row">
                <span className="widget-row-icon">📋</span>
                <div>
                  <div className="widget-row-text" style={{ cursor: 'pointer' }} onClick={() => navigate('/briefing?topic=markets')}>Markets Briefing</div>
                  <div className="widget-row-sub">AI-curated sector report</div>
                </div>
              </div>
              <div className="widget-row">
                <span className="widget-row-icon">💬</span>
                <div>
                  <div className="widget-row-text" style={{ cursor: 'pointer' }} onClick={() => navigate('/chat')}>Catch Me Up</div>
                  <div className="widget-row-sub">Chat with the AI about news</div>
                </div>
              </div>
              <div className="widget-row">
                <span className="widget-row-icon">🏦</span>
                <div>
                  <div className="widget-row-text" style={{ cursor: 'pointer' }} onClick={() => navigate('/briefing?topic=rbi')}>RBI & Policy</div>
                  <div className="widget-row-sub">Latest monetary updates</div>
                </div>
              </div>
            </div>

            {/* What's hot widget */}
            <div className="widget">
              <p className="widget-title">What's Hot 🔥</p>
              <div className="widget-row">
                <span className="widget-row-icon">📈</span>
                <div>
                  <div className="widget-row-text">Markets</div>
                  <div className="widget-row-sub">Sensex · Nifty · BSE</div>
                </div>
              </div>
              <div className="widget-row">
                <span className="widget-row-icon">🚀</span>
                <div>
                  <div className="widget-row-text">Startups</div>
                  <div className="widget-row-sub">Funding · Unicorns · IPOs</div>
                </div>
              </div>
              <div className="widget-row">
                <span className="widget-row-icon">🏏</span>
                <div>
                  <div className="widget-row-text">IPL 2026</div>
                  <div className="widget-row-sub">Scores · Fixtures · Teams</div>
                </div>
              </div>
              <a className="widget-link" onClick={() => navigate('/briefing')}>View all briefings →</a>
            </div>

            {/* Platform stats widget */}
            <div className="widget">
              <p className="widget-title">Platform</p>
              <div className="widget-stat-row">
                <div className="widget-stat"><div className="num">AI</div><div className="lbl">Powered</div></div>
                <div className="widget-stat"><div className="num">3</div><div className="lbl">Languages</div></div>
                <div className="widget-stat"><div className="num">∞</div><div className="lbl">Real-time</div></div>
              </div>
              <a className="widget-link" onClick={() => navigate('/chat')}>Ask AI anything →</a>
            </div>
          </aside>
        </div>
      </div>

      {/* Translation Modal */}
      {transOpen && (
        <Modal onClose={() => setTransOpen(false)}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>{transTitle}</h2>
          {transLoading ? <Spinner center /> : (
            <p style={{ fontSize: '0.95rem', lineHeight: 1.75, color: 'var(--text-secondary)' }}>{transText}</p>
          )}
        </Modal>
      )}

      {/* AI Reporter Modal */}
      {reporterArticle && (
        <AIReporter article={reporterArticle} onClose={() => setReporterArticle(null)} />
      )}
    </div>
  )
}
