import { useRef, useEffect, useState } from 'react'
import Modal from '../components/Modal'
import Spinner from '../components/Spinner'
import { fetchReporterSummary } from '../api'
import type { Article } from '../api'

interface Props {
  article: Article
  onClose: () => void
}

export default function AIReporter({ article, onClose }: Props) {
  const [summary, setSummary] = useState('')
  const [status, setStatus] = useState('Fetching summary…')
  const [playing, setPlaying] = useState(false)
  const [ready, setReady] = useState(false)
  const [words, setWords] = useState<string[]>([])
  const [activeIdx, setActiveIdx] = useState(-1)
  const [visibleUpTo, setVisibleUpTo] = useState(-1)
  const wordIdxRef = useRef(0)
  const anchorRef = useRef<HTMLDivElement>(null)
  const synth = window.speechSynthesis

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const text = await fetchReporterSummary(article._id)
        if (cancelled) return
        const s = text || `${article.title}. ${article.description || ''}`
        setSummary(s)
        setWords(s.split(' '))
        setStatus('Ready! Press Play to hear the summary')
        setReady(true)
      } catch {
        if (cancelled) return
        const fallback = `${article.title}. ${article.description || ''}`
        setSummary(fallback)
        setWords(fallback.split(' '))
        setStatus('Press Play to hear the summary')
        setReady(true)
      }
    }
    load()
    return () => { cancelled = true; synth.cancel() }
  }, [article._id])

  function buildUtterance(text: string) {
    const u = new SpeechSynthesisUtterance(text)
    const voices = synth.getVoices()
    const male = voices.find(v =>
      (v.lang === 'en-IN' || v.lang === 'hi-IN') &&
      (v.name.toLowerCase().includes('male') || v.name.includes('Rishi') || v.name.includes('Ravi'))
    ) || voices.find(v => v.lang === 'en-IN') || voices[0]
    if (male) u.voice = male
    u.lang = 'en-IN'
    u.rate = 0.95
    u.pitch = 0.8

    wordIdxRef.current = 0
    setActiveIdx(-1)
    setVisibleUpTo(-1)

    u.onboundary = (ev) => {
      if (ev.name === 'word') {
        const idx = wordIdxRef.current
        setVisibleUpTo(idx)
        setActiveIdx(idx)
        wordIdxRef.current = idx + 1
      }
    }
    u.onstart = () => {
      setStatus('● Reporting LIVE…')
      setPlaying(true)
      anchorRef.current?.classList.add('talking')
    }
    u.onend = () => {
      setStatus('✓ Report complete!')
      setPlaying(false)
      setVisibleUpTo(words.length)
      setActiveIdx(-1)
      anchorRef.current?.classList.remove('talking')
    }
    u.onerror = () => { setPlaying(false); anchorRef.current?.classList.remove('talking') }
    return u
  }

  function toggle() {
    if (!synth) return
    if (synth.paused) {
      synth.resume()
      setPlaying(true)
      setStatus('● Reporting LIVE…')
      anchorRef.current?.classList.add('talking')
    } else if (synth.speaking && playing) {
      synth.pause()
      setPlaying(false)
      setStatus('Paused')
      anchorRef.current?.classList.remove('talking')
    } else {
      synth.cancel()
      synth.speak(buildUtterance(summary))
    }
  }

  function handleClose() {
    synth.cancel()
    onClose()
  }

  const liveMode = playing

  return (
    <Modal onClose={handleClose} className="reporter-box">
      <div className="reporter-layout">
        {/* Anchor side */}
        <div ref={anchorRef} className="reporter-anchor-side">
          <img src="/static/ai_anchor.gif" alt="AI Reporter" />
          <div className={`reporter-signal ${liveMode ? 'live' : ''}`} />
          <div className={`reporter-live-badge ${liveMode ? 'show' : ''}`}>● ON AIR</div>
        </div>

        {/* Content side */}
        <div className="reporter-content">
          <span className="reporter-badge">🎙️ LIVE · AI REPORTER</span>
          <p className="reporter-title">{article.title}</p>

          <div className="reporter-summary-box">
            {words.length === 0 && <Spinner />}
            {words.map((w, i) => (
              <span
                key={i}
                className={`word ${i <= visibleUpTo ? 'visible' : ''} ${i === activeIdx ? 'active' : ''}`}
              >
                {w}{' '}
              </span>
            ))}
          </div>

          <p className="reporter-status">{status}</p>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button
              className="btn btn-primary"
              style={{ borderRadius: '50px', padding: '0.6rem 1.5rem' }}
              disabled={!ready}
              onClick={toggle}
            >
              {!ready ? '⏳ Loading…' : playing ? '⏸ Pause' : synth.paused ? '▶ Resume' : '▶ Play'}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}
