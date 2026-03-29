"""
MongoDB driver abstraction with full LocalMock fallback.
Ensures ALL agent functions remain functional even if Atlas connection fails.
"""

import os
import json
import uuid
import asyncio
import pymongo
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "NewsSpark")

_client: pymongo.MongoClient = None
_db: pymongo.database.Database = None
MOCK_MODE = True

# --- Local Caches ---
_SAMPLE_NEWS = []
_MOCK_LENSES = {} # article_id -> lenses

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
    await asyncio.to_thread(init_mongo_sync)

def init_mongo_sync():
    global _client, _db, MOCK_MODE
    print(f"[MongoDB] Connecting to: {MONGO_URI}")
    try:
        import certifi
        _client = pymongo.MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=3000,
            tlsCAFile=certifi.where() if "mongodb+srv" in MONGO_URI else None,
            tlsAllowInvalidCertificates=True
        )
        _db = _client[MONGO_DB_NAME]
        _client.admin.command('ping')
        print(f"[MongoDB] SUCCESS: Connected to '{MONGO_DB_NAME}'.")
        MOCK_MODE = False
    except Exception as e:
        print(f"[MongoDB] FAILED ({e}). Switching to MOCK_MODE.")
        MOCK_MODE = True
        _client = _db = None

def get_db():
    global _db, MOCK_MODE
    if MOCK_MODE: return None
    if _db is None: 
        try: init_mongo_sync()
        except: return None
    return _db

# --- User operations ---

async def upsert_user(user: dict):
    db = get_db()
    if db is None: return
    update_fields = {k: user[k] for k in ("name", "role", "avatar", "interests", "email", "language") if k in user}
    def _sync():
        db["user_profiles"].update_one({"_id": user["user_id"]}, {"$set": update_fields, "$setOnInsert": {"behavior": {"bookmarks": []}}}, upsert=True)
    await asyncio.to_thread(_sync)

async def get_user_by_id(user_id: str) -> dict | None:
    db = get_db()
    if db is None:
        from db.demo_users import DEMO_USERS
        for u in DEMO_USERS.values():
            if u.get("user_id") == user_id: 
                doc = u.copy()
                doc["_id"] = doc["user_id"]
                return doc
        doc = DEMO_USERS.get("investor").copy()
        doc["_id"] = doc["user_id"]
        return doc
    return await asyncio.to_thread(db["user_profiles"].find_one, {"_id": user_id})

async def update_user_behavior(user_id: str, action: str, category: str, source: str = ""): pass
async def add_user_bookmark(user_id: str, article_id: str): pass

# --- Article operations ---

async def save_article(article: dict):
    db = get_db()
    if db is None:
        # Prepend to mock cache so user sees new news immediately
        global _SAMPLE_NEWS
        if not any(a.get("url") == article.get("url") for a in _SAMPLE_NEWS):
            if "_id" not in article or not article["_id"]:
                # Use url_hash for stable unique ID, fall back to UUID
                article["_id"] = article.get("url_hash") or str(uuid.uuid4())
            _SAMPLE_NEWS.insert(0, article)
            _SAMPLE_NEWS = _SAMPLE_NEWS[:500]  # Cap at 500 to hold more articles
            print(f"[Mock] Saved new article to memory: {article.get('title', '')[:50]}...")
        return article
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
        if not categories or "all" in categories or "top" in categories:
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
        # Search both sample_news and live-fetched in-memory articles
        for a in _SAMPLE_NEWS:
            a_id = str(a.get("_id", ""))
            if (a_id == article_id
                    or str(a.get("story_cluster_id", "")) == article_id
                    or str(a.get("url_hash", "")) == article_id):
                return a
        # Nothing found — return None (do NOT fall back to index 0)
        print(f"[Mock] get_article_by_id({article_id}): not found in {len(_SAMPLE_NEWS)} articles")
        return None

    def _sync():
        try: return db["articles"].find_one({"_id": ObjectId(article_id)})
        except: return None
    return await asyncio.to_thread(_sync)

async def get_articles_by_ids(article_ids: list[str]) -> list:
    db = get_db()
    if db is None:
        return [a for a in _SAMPLE_NEWS if str(a.get("_id")) in article_ids or str(a.get("url_hash")) in article_ids][:len(article_ids)]
    def _sync():
        oids = []
        for aid in article_ids:
            try: oids.append(ObjectId(aid))
            except: pass
        return list(db["articles"].find({"_id": {"$in": oids}})) if oids else []
    return await asyncio.to_thread(_sync)

async def get_articles_by_cluster(cluster_id: str, limit: int = 20):
    db = get_db()
    if db is None:
        # Use _SAMPLE_NEWS (live store) not _load_sample_news() (static file only)
        matches = [a for a in _SAMPLE_NEWS if a.get("story_cluster_id") == cluster_id]
        print(f"[DB] Mock get_articles_by_cluster({cluster_id}): found {len(matches)} matches in {len(_SAMPLE_NEWS)} articles")
        return matches[:limit]
    def _sync():
        return list(db["articles"].find({"story_cluster_id": cluster_id}, sort=[("published_at", -1)], limit=limit))
    return await asyncio.to_thread(_sync)

async def update_article_lenses(article_id: str, lenses: dict):
    if MOCK_MODE: _MOCK_LENSES[article_id] = lenses; return
    db = get_db()
    if db is not None:
        try: await asyncio.to_thread(db["articles"].update_one, {"_id": ObjectId(article_id)}, {"$set": {"lenses": lenses}})
        except: pass

async def get_article_lenses(article_id: str):
    if MOCK_MODE: return _MOCK_LENSES.get(article_id)
    db = get_db()
    if db is not None:
        try: 
            doc = await asyncio.to_thread(db["articles"].find_one, {"_id": ObjectId(article_id)}, {"lenses": 1})
            return doc.get("lenses") if doc else None
        except: return None
    return None

_MOCK_ARCS = {} # topic -> arc

async def upsert_story_arc(arc: dict):
    if MOCK_MODE:
        _MOCK_ARCS[arc["_id"]] = arc
        return
    db = get_db()
    if db is not None:
        await asyncio.to_thread(
            db["story_arcs"].replace_one,
            {"_id": arc["_id"]},
            arc,
            upsert=True
        )

async def get_story_arc(topic: str):
    if MOCK_MODE:
        return _MOCK_ARCS.get(topic)
    db = get_db()
    if db is not None:
        return await asyncio.to_thread(db["story_arcs"].find_one, {"_id": topic})
    return None
async def update_article_gif(article_id: str, base64_gif: str): pass

async def close_mongo():
    global _client
    if _client is not None:
        _client.close()
        print("[MongoDB] Connection closed.")
