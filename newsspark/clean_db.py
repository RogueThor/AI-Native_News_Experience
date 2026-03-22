import asyncio
import os
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "newsspark")

def _clean_content(raw_html: str) -> tuple[str, str | None]:
    if not raw_html:
        return "", None
    soup = BeautifulSoup(raw_html, "html.parser")
    img = soup.find("img")
    img_url = img.get("src") if img else None
    text = soup.get_text(separator=" ").strip()
    return text, img_url

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    count = 0
    updated = 0
    cursor = db.articles.find({})
    async for article in cursor:
        count += 1
        needs_update = False
        updates = {}
        
        # 1. Clean HTML tags
        desc = article.get("description", "")
        content = article.get("content", "")
        
        # Check if description or content contains HTML tags
        has_html = "<" in desc or "<" in content
        
        text, img_url = _clean_content(desc or content)
        
        if has_html or "<" in article.get("raw_text", ""):
            updates["description"] = text[:500]
            updates["content"] = text[:5000]
            updates["raw_text"] = text
            needs_update = True
            
        # 2. Add missing image
        if not article.get("image_url") and img_url:
            updates["image_url"] = img_url
            needs_update = True
            
        # 3. Add missing cluster ID
        if not article.get("story_cluster_id") or "1" in article.get("story_cluster_id", "") or len(article.get("story_cluster_id", "")) < 4:
            cat = article.get("category", "other")
            updates["story_cluster_id"] = f"{cat}_{datetime.utcnow().strftime('%Y%m%d')}"
            needs_update = True
        elif len(article.get("story_cluster_id", "").split("_")) == 1:
            # Upgrade old format "politics" to "politics_20260322"
            cat = article.get("story_cluster_id")
            updates["story_cluster_id"] = f"{cat}_{datetime.utcnow().strftime('%Y%m%d')}"
            needs_update = True
            
        if needs_update:
            await db.articles.update_one({"_id": article["_id"]}, {"$set": updates})
            updated += 1
            
    print(f"Total articles: {count}, Updated: {updated}")
    
if __name__ == "__main__":
    asyncio.run(main())
