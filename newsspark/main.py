"""
main.py — NewsSpark FastAPI application entry point.
Handles startup (MongoDB, SQLite, ChromaDB, demo users, scheduler),
session middleware, static files, and router includes.
"""

import os
import asyncio
import sys

# Windows-specific fix for motor/asyncio SSL issues
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from db.sqlite import init_sqlite
from db.demo_users import DEMO_USERS
from db.mongo import upsert_user

load_dotenv()

SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "newsspark-super-secret-key-change-me")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

scheduler = AsyncIOScheduler()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    import traceback
    try:
        # 1. Initialize DBs
        from db.mongo import init_mongo_sync
        await asyncio.to_thread(init_mongo_sync)
        
        from db.sqlite import init_sqlite
        await init_sqlite()
        
        # Upsert all demo users into MongoDB (if connected)
        try:
            from db.demo_users import DEMO_USERS
            from db.mongo import upsert_user
            for user_data in DEMO_USERS.values():
                await upsert_user(user_data)
            print("[Startup] Demo users upserted.")
        except Exception as e:
            print(f"[Startup] Demo user upsert skip: {e}")

        # Initialize ChromaDB (CAUTION: can panic on some Windows setups)
        try:
            from db.chroma import init_chroma
            import db.chroma as chroma_module
            # init_chroma is known to cause Rust panics on certain Windows environments.
            # We skip it and explicitly disable ChromaDB to prevent lazy init.
            # await asyncio.to_thread(init_chroma) 
            chroma_module.CHROMA_DISABLED = True
            print("[Startup] ChromaDB explicitly DISABLED (avoiding Rust panic on Windows).")
        except Exception as e:
            print(f"[Startup] ChromaDB error: {e}")

        # Start the fetcher agent
        try:
            from agents.fetcher_agent import scheduled_fetch
            asyncio.create_task(scheduled_fetch())
            print("[Startup] Fetcher task started.")
            
            if not scheduler.running:
                scheduler.add_job(scheduled_fetch, "interval", minutes=30)
                scheduler.start()
                print("[Scheduler] Started.")
        except Exception as e:
            print(f"[Startup] Scheduler/Fetcher error: {e}")

        yield

    except Exception as e:
        print(f"!!! FATAL LIFESPAN ERROR !!!: {e}")
        traceback.print_exc()
        raise e
    finally:
        # Cleanup
        try:
            from db.mongo import close_mongo
            await close_mongo()
        except: pass
        if scheduler.running:
            scheduler.shutdown()
        print("[Shutdown] Closed connections.")


# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NewsSpark",
    description="AI-Native Indian News Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Middleware & Routes ───────────────────────────────────────────────────────

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="newsspark_session",
    max_age=3600 * 24 * 7,
)

# Static files from the legacy frontend (GIF, etc.)
_static_dir = os.path.join(BASE_DIR, "frontend", "static")
if os.path.isdir(_static_dir):
    app.mount(
        "/static",
        StaticFiles(directory=_static_dir),
        name="static",
    )


# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/")
async def root(request: Request):
    user_id = request.session.get("user_id")
    if user_id:
        return RedirectResponse(url="/feed")
    return RedirectResponse(url="/login")


# ── Include existing routes ───────────────────────────────────────────────────

from routes.user import router as user_router
from routes.news import router as news_router
from routes.arc import router as arc_router

app.include_router(user_router)
app.include_router(news_router)
app.include_router(arc_router)

@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": os.getenv("MOCK_MODE", "auto")}



# ── Include new routers ───────────────────────────────────────────────────────

from routers.feed import router as feed_ws_router
from routers.articles import router as articles_router
from routers.chat import router as chat_router
from routers.users import router as users_router

app.include_router(feed_ws_router)
app.include_router(articles_router)
app.include_router(chat_router)
app.include_router(users_router)


# ── Dev entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # Passing the app object directly (not string) and disabling reload 
    # provides the most stable SSL environment on Windows/Python 3.13
    uvicorn.run(app, host="127.0.0.1", port=8000)
