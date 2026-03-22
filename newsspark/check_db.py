import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def check():
    client = AsyncIOMotorClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))
    db = client[os.getenv('MONGO_DB_NAME', 'newsspark')]
    docs = await db.articles.find({'title': {'$regex': 'Realme 16 5G|dual dependence on West Asia'}}).to_list(None)
    for d in docs:
        print(f"Title: {d.get('title')}")
        print(f"Story Cluster: '{d.get('story_cluster_id')}'")
        print(f"Image URL: '{d.get('image_url')}'")
        print('-'*20)

if __name__ == '__main__':
    asyncio.run(check())
