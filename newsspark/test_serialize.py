import sys
import asyncio, json
import os

# Ensure we can import from db
sys.path.append(os.path.dirname(__file__))

from db.mongo import init_mongo, get_all_recent_articles
from agents.personalize import _serialize_article

async def main():
    await init_mongo()
    res = await get_all_recent_articles(5)
    for a in res:
        sa = _serialize_article(a)
        print("has_id:", "_id" in sa, "type:", type(sa.get("_id")), sa.get("title")[:20])

asyncio.run(main())
