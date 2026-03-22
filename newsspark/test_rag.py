import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def test_rag():
    from db.mongo import init_mongo
    await init_mongo()
    
    from agents.personalize_agent import run_personalize
    state = {
        "user_id": "test_user",
        "user_profile": {"role": "general", "interests": ["technology", "business"]},
    }
    
    result = await run_personalize(state)
    feed = result.get("feed", [])
    
    print(f"Total feed items returned by personalize_agent: {len(feed)}")
    if feed:
        print("First item keys:", list(feed[0].keys()))
        print("First item metadata:")
        print(f"  Title: {feed[0].get('title')}")
        print(f"  story_cluster_id: {feed[0].get('story_cluster_id')}")
        print(f"  image_url: {feed[0].get('image_url')}")
    else:
        print("Feed is empty!")

if __name__ == "__main__":
    asyncio.run(test_rag())
