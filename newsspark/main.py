"""
main.py – NewsSpark FastAPI application entry point.
Handles startup (MongoDB, SQLite, demo users, scheduler), 
session middleware, static files, templates, and router includes.
"""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from db.mongo import init_mongo, get_db
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
    # Startup
    await init_mongo()
    await init_sqlite()

    # Upsert all demo users into MongoDB
    for user in DEMO_USERS.values():
        await upsert_user(user)
    print("[Startup] Demo users upserted to MongoDB.")

    # Run Agent 1 once immediately
    from agents.fetcher import scheduled_fetch
    asyncio.create_task(scheduled_fetch())
    print("[Startup] Initial news fetch started.")

    # Schedule Agent 1 every 30 minutes
    scheduler.add_job(scheduled_fetch, "interval", minutes=30)
    scheduler.start()
    print("[Scheduler] News fetch scheduled every 30 minutes.")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    print("[Shutdown] Scheduler stopped.")


# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NewsSpark",
    description="AI-Native Vernacular Business News Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Session middleware (required for request.session)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="newsspark_session",
    max_age=86400,  # 1 day
    https_only=False,
)

# Static files
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static")),
    name="static",
)

# Templates (only used in routers, but also available here)
templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "frontend", "templates")
)


# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/")
async def root(request: Request):
    user_id = request.session.get("user_id")
    if user_id:
        return RedirectResponse(url="/feed")
    return RedirectResponse(url="/login")


# ── Include routers ───────────────────────────────────────────────────────────

from routes.user import router as user_router
from routes.news import router as news_router
from routes.arc import router as arc_router

app.include_router(user_router)
app.include_router(news_router)
app.include_router(arc_router)


# ── Dev entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
