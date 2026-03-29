import asyncio
import os
from db.mongo import init_mongo_sync, get_articles_by_cluster, MOCK_MODE

async def main():
    # Force mock mode for testing
    print("Initialising DB...")
    init_mongo_sync()
    
    topic = "r-ai-123"
    articles = await get_articles_by_cluster(topic)
    print(f"Topic: {topic}")
    print(f"Articles found: {len(articles)}")
    for a in articles:
        print(f" - {a.get('title')} (Cluster: {a.get('story_cluster_id')})")

if __name__ == "__main__":
    os.environ["MOCK_MODE"] = "true"
    asyncio.run(main())
