import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def test_direct():
    from db.mongo import init_mongo
    await init_mongo()
    
    from pipeline.graph import graph
    state = {
        "request_type": "feed",
        "user_id": "test_user",
        "user_profile": {"role": "general", "interests": ["business"]},
    }
    
    result = await graph.ainvoke(state)
    feed = result.get("feed", [])
    
    print(f"Total feed items returned: {len(feed)}")
    for i, a in enumerate(feed[:3]):
        print(f"[{i}] {a.get('title')}")
        print(f"  image_url: {a.get('image_url')}")
        print(f"  story_cluster_id: {a.get('story_cluster_id')}")

if __name__ == "__main__":
    asyncio.run(test_direct())
