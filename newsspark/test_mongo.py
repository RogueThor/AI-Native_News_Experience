import os
from pymongo import MongoClient
from dotenv import load_dotenv
import ssl
import uvicorn
print(f"Uvicorn version: {uvicorn.__version__}")

load_dotenv()
uri = os.getenv("MONGO_URI")
db_name = os.getenv("MONGO_DB_NAME", "NewsSpark")
print(f"Testing connection to: {uri.split('@')[1] if '@' in uri else uri}")

try:
    # Try with default SSL
    print("\n[Scenario 1] Default SSL...")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    print(f"Connected to {db.name}")
    print("Collections:", db.list_collection_names()[:5])
except Exception as e:
    print(f"Default SSL Failed: {e}")
    
    try:
        # Try with certifi
        import certifi
        print("\n[Scenario 2] Retrying with certifi CA bundle...")
        client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        db = client[db_name]
        print(f"Certifi SSL: Connected to {db.name}")
        print("Collections:", db.list_collection_names()[:5])
    except Exception as e2:
        print(f"Certifi SSL Failed: {e2}")

        try:
            # Try bypassing SSL (DEBUG ONLY)
            print("\n[Scenario 3] Bypassing SSL validation (DEBUG ONLY)...")
            client = MongoClient(uri, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
            db = client[db_name]
            print(f"Bypassed SSL: Connected to {db.name}")
            print("Collections:", db.list_collection_names()[:5])
        except Exception as e3:
            print(f"All SSL scenarios failed: {e3}")
