import os
import sys
from dotenv import load_dotenv

# 1. Load env and connect to Mongo IMMEDIATELY before ANY other imports
load_dotenv()
from db.mongo import init_mongo_sync
try:
    init_mongo_sync()
except Exception as e:
    print(f"[RunApp] Fatal Early Mongo Error: {e}")

# 2. Force Windows Selector Loop and bypass SSL verification (NUCLEAR OPTION)
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,  # Still False for stability
    )
