import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env from root folder (one level up from newsspark/)
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

print(f"🔍 MONGO_URI     : {MONGO_URI}")
print(f"🔍 MONGO_DB_NAME : {MONGO_DB_NAME}")

async def test_connection():
    if not MONGO_URI or not MONGO_DB_NAME:
        print("\n❌ .env not loaded! Check:")
        print("  - .env file exists in AI-Native_News_Experience/ root")
        print("  - No spaces around '=' in .env")
        print("  - Variables named exactly: MONGO_URI and MONGO_DB_NAME")
        return

    print(f"\n🔄 Connecting to: {MONGO_DB_NAME}...")

    try:
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB_NAME]

        # Ping server
        await client.admin.command("ping")
        print("✅ MongoDB connected successfully!")

        # List collections
        collections = await db.list_collection_names()
        print(f"📦 Collections: {collections if collections else '[] (empty — normal for new DB)'}")

        # Test insert
        result = await db["test"].insert_one({"test": "newsspark", "status": "ok"})
        print(f"✅ Test insert successful! ID: {result.inserted_id}")

        # Test read
        doc = await db["test"].find_one({"test": "newsspark"})
        print(f"✅ Test read successful! Doc: {doc}")

        # Cleanup
        await db["test"].drop()
        print("🧹 Test collection cleaned up")

        print("\n🎉 ALL TESTS PASSED — MongoDB is ready!")

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n🔍 Check:")
        print("  1. IP whitelisted in Atlas → Network Access → 0.0.0.0/0")
        print("  2. Username/password correct in MONGO_URI")
        print("  3. Special characters in password URL-encoded")
        print("  4. MONGO_URI ends with ?retryWrites=true&w=majority")

asyncio.run(test_connection())
