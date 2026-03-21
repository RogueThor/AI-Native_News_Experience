"""
MongoDB async driver setup using motor.
Provides get_db() helper and collection accessors.
"""

import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "newsspark")

_client: motor.motor_asyncio.AsyncIOMotorClient = None
_db: motor.motor_asyncio.AsyncIOMotorDatabase = None


async def init_mongo():
    """Initialize MongoDB connection and store globally."""
    global _client, _db
    _client = motor.motor_asyncio.AsyncIOMotorClient(
        MONGO_URI,
        tlsAllowInvalidCertificates=True
    )
    _db = _client[MONGO_DB_NAME]
    # Ensure indexes
    await _db["articles"].create_index("url", unique=True)
    await _db["articles"].create_index("story_cluster_id")
    await _db["articles"].create_index("category")
    await _db["story_arcs"].create_index("topic_name")
    print(f"[MongoDB] Connected to '{MONGO_DB_NAME}' at {MONGO_URI}")


def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Return the active database instance."""
    if _db is None:
        raise RuntimeError("MongoDB is not initialized. Call init_mongo() first.")
    return _db


async def get_collection(name: str) -> motor.motor_asyncio.AsyncIOMotorCollection:
    """Return a named collection from the active database."""
    return get_db()[name]


async def upsert_user(user: dict):
    """Upsert a user profile into MongoDB by user_id."""
    db = get_db()
    await db["user_profiles"].update_one(
        {"_id": user["user_id"]},
        {"$set": {
            "name": user["name"],
            "role": user["role"],
            "language_pref": user["language_pref"],
            "avatar": user["avatar"],
            "interests": user["interests"],
        }},
        upsert=True
    )


async def get_user_by_id(user_id: str) -> dict | None:
    """Fetch a user profile by _id."""
    db = get_db()
    doc = await db["user_profiles"].find_one({"_id": user_id})
    return doc


async def save_article(article: dict):
    """Insert article if URL is not already present (dedup by url)."""
    db = get_db()
    try:
        await db["articles"].insert_one(article)
    except Exception:
        # Duplicate key on url index — skip silently
        pass


async def get_articles_by_cluster(cluster_id: str, limit: int = 20) -> list:
    """Fetch articles belonging to a story cluster."""
    db = get_db()
    cursor = db["articles"].find(
        {"story_cluster_id": cluster_id},
        sort=[("published_at", -1)],
        limit=limit
    )
    return await cursor.to_list(length=limit)


async def get_articles_by_category(categories: list, limit: int = 20) -> list:
    """Fetch recent articles matching a list of categories."""
    db = get_db()
    query = {"category": {"$in": categories}} if categories else {}
    cursor = db["articles"].find(
        query,
        sort=[("published_at", -1)],
        limit=limit
    )
    return await cursor.to_list(length=limit)


async def get_all_recent_articles(limit: int = 20) -> list:
    """Fetch the most recent articles regardless of category."""
    db = get_db()
    cursor = db["articles"].find(
        {},
        sort=[("published_at", -1)],
        limit=limit
    )
    return await cursor.to_list(length=limit)


async def get_article_by_id(article_id: str) -> dict | None:
    """Fetch a single article by its string _id."""
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(article_id)
        return await db["articles"].find_one({"_id": oid})
    except Exception:
        return None


async def upsert_story_arc(arc: dict):
    """Upsert a story arc by its _id (topic key)."""
    db = get_db()
    arc_id = arc.pop("_id", None) or arc.get("topic_name", "unknown")
    await db["story_arcs"].update_one(
        {"_id": arc_id},
        {"$set": arc},
        upsert=True
    )


async def update_article_gif(article_id: str, base64_gif: str):
    """Store the generated GIF back in the article document for caching."""
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(article_id)
        await db["articles"].update_one(
            {"_id": oid},
            {"$set": {"base64_gif": base64_gif}}
        )
    except Exception:
        pass


async def get_story_arc(topic: str) -> dict | None:
    """Fetch a story arc by topic key."""
    db = get_db()
    return await db["story_arcs"].find_one({"_id": topic})


async def close_mongo():
    """Close the MongoDB connection."""
    global _client
    if _client:
        _client.close()
        print("[MongoDB] Connection closed.")
