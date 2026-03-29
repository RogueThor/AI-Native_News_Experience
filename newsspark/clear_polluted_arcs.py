import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["NewsSpark"]
coll = db["story_arcs"]

print("Deleting ALL Articles and Story Arcs to force clean state...")
res1 = db["articles"].delete_many({})
res2 = db["story_arcs"].delete_many({})
print(f"Deleted {res1.deleted_count} articles and {res2.deleted_count} arcs.")

client.close()
