"""
MongoDB driver abstraction with automatic LocalMock fallback.
Ensures the app remains functional even if Atlas connection fails on Windows.
"""

import os
import json
import asyncio
import pymongo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "NewsSpark")

_client: pymongo.MongoClient = None
_db: pymongo.database.Database = None
MOCK_MODE = False

# --- Helper to load sample data ---
_SAMPLE_NEWS = []
def _load_sample_news():
    global _SAMPLE_NEWS
    if _SAMPLE_NEWS: return _SAMPLE_NEWS
    try:
        path = os.path.join(os.path.dirname(__file__), "sample_news.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                _SAMPLE_NEWS = json.load(f)
    except Exception as e:
        print(f"[Mock] Error loading sample_news.json: {e}")
    return _SAMPLE_NEWS

async def init_mongo():
    """Async wrapper for init_mongo_sync."""
    await asyncio.to_thread(init_mongo_sync)

def init_mongo_sync():
    """Initialize MongoDB connection synchronously with a quick failover."""
    global _client, _db, MOCK_MODE
    print(f"[MongoDB] Connecting to: {MONGO_URI}")
    
    try:
        # Use a short timeout for the initial connection check
        import certifi
        _client = pymongo.MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=3000,
            tlsCAFile=certifi.where() if "mongodb+srv" in MONGO_URI else None,
            tlsAllowInvalidCertificates=True
        )
        _db = _client[MONGO_DB_NAME]
        # Force a ping
        _client.admin.command('ping')
        print(f"[MongoDB] SUCCESS: Connected to '{MONGO_DB_NAME}'.")
        MOCK_MODE = False
    except Exception as e:
        print(f"[MongoDB] FAILED ({e}). Switching to MOCK_MODE.")
        MOCK_MODE = True
        _client = None
        _db = None

def get_db():
    global _db, MOCK_MODE
    if MOCK_MODE: return None
    if _db is None:
        try:
            init_mongo_sync()
        except:
            return None
    return _db

# --- User operations ---

async def upsert_user(user: dict):
    db = get_db()
    if db is None: 
        print(f"[Mock] Upserted user {user.get('user_id')} (Local only)")
        return
    
    update_fields = {k: user[k] for k in ("name", "role", "avatar", "interests", "email", "language") if k in user}
    def _sync():
        db["user_profiles"].update_one(
            {"_id": user["user_id"]},
            {"$set": update_fields, "$setOnInsert": {"behavior": {"bookmarks": []}}},
            upsert=True
        )
    await asyncio.to_thread(_sync)

async def get_user_by_id(user_id: str) -> dict | None:
    db = get_db()
    if db is None:
        from db.demo_users import DEMO_USERS
        # Try to find mock user by user_id or role
        for u in DEMO_USERS.values():
            if u.get("user_id") == user_id: return u
        # Fallback to investor if not found
        return DEMO_USERS.get("investor")
        
    return await asyncio.to_thread(db["user_profiles"].find_one, {"_id": user_id})

# --- Article operations ---

async def save_article(article: dict):
    db = get_db()
    if db is None: return None
    def _sync():
        try:
            res = db["articles"].insert_one(article)
            article["_id"] = res.inserted_id
            return article
        except: return None
    return await asyncio.to_thread(_sync)

async def get_articles_by_category(categories: list, limit: int = 20) -> list:
    db = get_db()
    if db is None:
        data = _load_sample_news()
        if not categories or "all" in categories:
            return data[:limit]
        return [a for a in data if a.get("category") in categories][:limit]

    def _sync():
        query = {"category": {"$in": categories}} if categories else {}
        return list(db["articles"].find(query, sort=[("published_at", -1)], limit=limit))
    return await asyncio.to_thread(_sync)

async def get_all_recent_articles(limit: int = 20) -> list:
    return await get_articles_by_category([], limit)

async def get_article_by_id(article_id: str) -> dict | None:
    db = get_db()
    if db is None:
        data = _load_sample_news()
        # Mock ID lookup (usually article_id is a URL or title for mocks)
        for a in data:
            if str(a.get("story_cluster_id")) == article_id: return a
        return data[0] if data else None

    from bson import ObjectId
    def _sync():
        try: return db["articles"].find_one({"_id": ObjectId(article_id)})
        except: return None
    return await asyncio.to_thread(_sync)

# --- Other stubs ---
async def update_user_behavior(user_id: str, action: str, category: str, source: str = ""): pass
async def add_user_bookmark(user_id: str, article_id: str): pass
async def get_articles_by_cluster(cluster_id: str, limit: int = 20): return []
async def update_article_lenses(article_id: str, lenses: dict): pass
async def get_article_lenses(article_id: str): return None
async def upsert_story_arc(arc: dict): pass
async def get_story_arc(topic: str): return None
async def update_article_gif(article_id: str, base64_gif: str): pass

async def close_mongo():
    global _client
    if _client:
        _client.close()
        print("[MongoDB] Connection closed.")
