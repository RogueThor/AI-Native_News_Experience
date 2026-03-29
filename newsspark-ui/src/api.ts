// api.ts — Typed helpers for all FastAPI endpoints

export interface Article {
  _id: string;
  title: string;
  description?: string;
  content?: string;
  url: string;
  image_url?: string;
  source?: string;
  source_name?: string;
  category?: string;
  sentiment?: 'positive' | 'negative' | 'neutral';
  published_at?: string;
  story_cluster_id?: string;
}

export interface FeedResponse {
  feed: Article[];
}

export interface TranslationResponse {
  translated_text: string;
}

export interface ReporterResponse {
  summary: string;
}

export interface ChatMessage {
  topic?: string;
  summary?: string;
  timeline?: { date: string; headline: string; sentiment: string }[];
  sources?: string[];
  _meta?: { chroma_count: number; used_live_search: boolean };
}

export interface BriefingResponse {
  briefing_text: string;
}

export interface AskResponse {
  answer_text: string;
}

export interface ArcData {
  _id: string;
  topic_name: string;
  last_updated?: string;
  timeline?: { date: string; headline: string; sentiment: string }[];
  key_players?: string[];
  sentiment_trend?: { date: string; score: number }[];
  what_to_watch_next?: string;
}

export interface ArcResponse {
  arc?: ArcData;
  topic: string;
}

export interface User {
  _id: string;
  name: string;
  avatar: string;
  role: string;
  language_pref?: string;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function loginWithRole(role: string): Promise<void> {
  const fd = new FormData();
  fd.append('role', role);
  await fetch('/login', { method: 'POST', body: fd, redirect: 'manual' });
}

// ── News Feed ─────────────────────────────────────────────────────────────────

export async function fetchFeed(category?: string): Promise<Article[]> {
  const url = category && category !== 'top'
    ? `/news/feed?category=${category}&t=${Date.now()}`
    : `/news/feed?t=${Date.now()}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('Failed to load feed');
  const data: FeedResponse = await resp.json();
  return data.feed || [];
}

export async function fetchTranslation(articleId: string, lang: 'tamil' | 'hindi'): Promise<string> {
  const resp = await fetch(`/news/translate/${articleId}?lang=${lang}`);
  const data: TranslationResponse = await resp.json();
  return data.translated_text || 'Translation not available.';
}

export async function fetchReporterSummary(articleId: string): Promise<string> {
  const resp = await fetch(`/news/reporter/${articleId}`);
  const data: ReporterResponse = await resp.json();
  return data.summary || '';
}

export async function trackInteraction(articleId: string, action: string): Promise<void> {
  if (!articleId) return;
  await fetch('/interaction', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ article_id: articleId, action }),
  });
}

// ── Briefing ──────────────────────────────────────────────────────────────────

export async function fetchBriefing(topic: string): Promise<string> {
  const resp = await fetch('/news/briefing', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  const data: BriefingResponse = await resp.json();
  return data.briefing_text || 'No briefing available.';
}

export async function askBriefingQuestion(topic: string, question: string): Promise<string> {
  const resp = await fetch('/news/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, question }),
  });
  const data: AskResponse = await resp.json();
  return data.answer_text || 'No response.';
}

// ── Arc ───────────────────────────────────────────────────────────────────────

export async function fetchArc(topic: string, refresh = false): Promise<ArcResponse> {
  const resp = await fetch(`/arc/data/${encodeURIComponent(topic)}${refresh ? '?refresh=true' : ''}`);
  return await resp.json();
}

// ── Session helpers ───────────────────────────────────────────────────────────

export async function fetchCurrentUser(): Promise<User | null> {
  try {
    const resp = await fetch('/user/me');
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}
