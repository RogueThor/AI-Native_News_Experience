import os
import asyncio
import motor.motor_asyncio
from dotenv import load_dotenv
import sys

# Try the loop fix here as well
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()
# Direct shard URI to bypass SRV SSL issues on Windows
uri = "mongodb://username:password@ac-zrgexzo-shard-00-00.ncqhh6k.mongodb.net:27017,ac-zrgexzo-shard-00-01.ncqhh6k.mongodb.net:27017,ac-zrgexzo-shard-00-02.ncqhh6k.mongodb.net:27017/?replicaSet=atlas-y8t3yz-shard-0&ssl=true&authSource=admin"
db_name = os.getenv("MONGO_DB_NAME", "NewsSpark")

async def test_motor():
    print(f"Testing MOTOR connection to: {uri.split('@')[1] if '@' in uri else uri}")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=20000)
        db = client[db_name]
        # Trigger actual connection
        cols = await db.list_collection_names()
        print(f"Motor Success! Connected to {db.name}")
        print("Collections:", cols[:5])
    except Exception as e:
        print(f"Motor Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_motor())
