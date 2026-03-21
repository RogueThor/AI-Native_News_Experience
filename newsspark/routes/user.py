"""
routes/user.py – Login, Logout, and User Profile endpoints.
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from db.demo_users import DEMO_USERS
from db.mongo import get_user_by_id, upsert_user

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_post(request: Request, role: str = Form(...)):
    user = DEMO_USERS.get(role)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Ensure user exists in MongoDB
    await upsert_user(user)

    # Set session cookie
    request.session["user_id"] = user["user_id"]

    response = RedirectResponse(url="/feed", status_code=303)
    return response


# ── Logout ────────────────────────────────────────────────────────────────────

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# ── User profile upsert ───────────────────────────────────────────────────────

@router.post("/user/profile")
async def upsert_profile(request: Request):
    body = await request.json()
    await upsert_user(body)
    return {"status": "ok"}
