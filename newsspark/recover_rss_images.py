import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

from sources.rss_fetcher import fetch_all_rss

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "newsspark")

async def main():
    print("Fetching fresh RSS to recover images...")
    articles, _ = await fetch_all_rss()
    
    print(f"Fetched {len(articles)} fresh RSS articles. Looking for missing images in DB...")
    
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    updated = 0
    for art in articles:
        if art.get("image_url"):
            # Update DB where url matches and image_url is missing
            result = await db.articles.update_many(
                {
                    "url": art["url"], 
                    "$or": [
                        {"image_url": None}, 
                        {"image_url": ""}
                    ]
                },
                {"$set": {"image_url": art["image_url"]}}
            )
            if result.modified_count > 0:
                print(f"Recovered image for: {art['title']}")
                updated += result.modified_count
                
    print(f"Total images recovered and updated in DB: {updated}")

if __name__ == "__main__":
    asyncio.run(main())
