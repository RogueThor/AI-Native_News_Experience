import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["NewsSpark"]
collection = db["articles"]

print("Latest 20 articles with their story_cluster_id:")
for doc in collection.find().sort("published_at", -1).limit(20):
    print(f"Title: {doc.get('title')}")
    print(f"Cluster: {doc.get('story_cluster_id')}")
    print("-" * 20)

client.close()
