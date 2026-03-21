"""
SQLite async layer for caching translations, briefings,
session logs, and agent logs using aiosqlite.
"""

import os
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "./newsspark_cache.db")


async def init_sqlite():
    """Create all tables if they don't exist."""
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                article_id TEXT,
                language   TEXT,
                translated_text TEXT,
                cached_at  TEXT,
                PRIMARY KEY (article_id, language)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS briefings (
                topic        TEXT PRIMARY KEY,
                summary_text TEXT,
                cached_at    TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT,
                article_id TEXT,
                action     TEXT,
                timestamp  TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name     TEXT,
                action         TEXT,
                input_summary  TEXT,
                output_summary TEXT,
                timestamp      TEXT
            )
        """)
        await db.commit()
    print(f"[SQLite] Tables initialised at {SQLITE_PATH}")


# ── Translation cache ─────────────────────────────────────────────────────────

async def get_translation(article_id: str, language: str) -> str | None:
    """Return cached translated text or None."""
    async with aiosqlite.connect(SQLITE_PATH) as db:
        async with db.execute(
            "SELECT translated_text FROM translations WHERE article_id=? AND language=?",
            (article_id, language)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def save_translation(article_id: str, language: str, translated_text: str):
    """Store a translation in the cache."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO translations (article_id, language, translated_text, cached_at)
            VALUES (?, ?, ?, ?)
            """,
            (article_id, language, translated_text, now)
        )
        await db.commit()


# ── Briefing cache ────────────────────────────────────────────────────────────

async def get_briefing(topic: str) -> str | None:
    """Return cached briefing text or None."""
    async with aiosqlite.connect(SQLITE_PATH) as db:
        async with db.execute(
            "SELECT summary_text FROM briefings WHERE topic=?",
            (topic,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def save_briefing(topic: str, summary_text: str):
    """Store a briefing in the cache."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO briefings (topic, summary_text, cached_at)
            VALUES (?, ?, ?)
            """,
            (topic, summary_text, now)
        )
        await db.commit()


# ── Session log ───────────────────────────────────────────────────────────────

async def log_session(user_id: str, article_id: str, action: str):
    """Record a user–article interaction."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (user_id, article_id, action, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, article_id, action, now)
        )
        await db.commit()


# ── Agent log ─────────────────────────────────────────────────────────────────

async def log_agent(
    agent_name: str,
    action: str,
    input_summary: str = "",
    output_summary: str = ""
):
    """Record an agent action for observability."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(
            """
            INSERT INTO agent_logs (agent_name, action, input_summary, output_summary, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent_name, action, input_summary, output_summary, now)
        )
        await db.commit()
