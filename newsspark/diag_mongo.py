import os
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import ssl

load_dotenv()

def check_db():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "NewsSpark")
    print(f"Connecting to {uri}, DB: {db_name}")
    try:
        # Match main app's SSL configuration
        client = MongoClient(
            uri, 
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where() if "mongodb+srv" in uri else None,
            tlsAllowInvalidCertificates=True
        )
        db = client[db_name]
        client.admin.command('ping')
        print("Connected successfully!")
        
        count = db.articles.count_documents({})
        print(f"Total articles in 'articles' collection: {count}")
        
        if count > 0:
            sample = db.articles.find_one()
            print(f"Sample Article:")
            print(f"  _id: {sample['_id']} ({type(sample['_id'])})")
            print(f"  title: {sample.get('title')}")
            
            print("\nFirst 5 IDs:")
            for d in db.articles.find({}, limit=5):
                print(f"  {d['_id']} ({type(d['_id'])})")
        else:
            print("Collection 'articles' is EMPTY.")
            print(f"Collections present: {db.list_collection_names()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
