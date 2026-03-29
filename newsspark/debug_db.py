import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["NewsSpark"]

total = db["articles"].count_documents({})
print(f"Total articles: {total}")

no_img = db["articles"].count_documents({
    "$or": [
        {"image_url": None},
        {"image_url": ""}
    ]
})
print(f"Articles missing image_url: {no_img}")

clusters = list(db["articles"].aggregate([
    {"$group": {"_id": "$story_cluster_id", "count": {"$sum": 1}}},
    {"$match": {"count": {"$gt": 1}}},
    {"$sort": {"count": -1}}
]))
print(f"Number of clusters with >1 articles: {len(clusters)}")
for c in clusters[:10]:
    print(f"  {c['_id']}: {c['count']}")

# Check timeline of the top cluster
if clusters:
    top_cluster = clusters[0]['_id']
    print(f"\nArticles in {top_cluster}:")
    for a in db["articles"].find({"story_cluster_id": top_cluster}):
        img = a.get("image_url")
        print(f" - {a['title'][:50]}... | Img: {bool(img)}")
