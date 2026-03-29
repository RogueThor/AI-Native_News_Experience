import asyncio
import os
from dotenv import load_dotenv
from agents.fetcher_agent import run_fetcher as fetch_and_classify
from pymongo import MongoClient

load_dotenv()

async def clean_and_fetch():
    # 1. HARD WIPE
    print("Hard wiping MongoDB...")
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["NewsSpark"]
    db["articles"].delete_many({})
    db["story_arcs"].delete_many({})
    print("Wipe complete.")
    
    await fetch_and_classify({})
    print("Fetch complete.")
    
    # 3. VERIFY
    count = db["articles"].count_documents({})
    print(f"Total articles in DB: {count}")
    
    # Check for clusters with > 1
    clusters = db["articles"].aggregate([
        {"$group": {"_id": "$story_cluster_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1}}
    ])
    print("Clusters with multiple articles:")
    for c in clusters:
        print(f"  {c['_id']}: {c['count']}")

if __name__ == "__main__":
    asyncio.run(clean_and_fetch())
