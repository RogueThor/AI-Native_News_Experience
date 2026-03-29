"""
Agent 6 – Image Animator
Downloads a news image and generates a Ken Burns GIF entirely in memory.
Returns a base64-encoded data URI or None if download fails.
"""

import io
import base64
import asyncio

import httpx
from PIL import Image

from db.sqlite import log_agent

FRAMES = 10          # GIF frame count
ZOOM_START = 1.0
ZOOM_END = 1.15
GIF_WIDTH = 640
GIF_HEIGHT = 360
FRAME_DURATION = 80  # ms per frame


def _generate_ken_burns(image_bytes: bytes) -> str | None:
    """
    Apply a Ken Burns zoom-pan effect and return a base64 data URI string.
    Runs synchronously; call via run_in_executor.
    """
    try:
        src = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        src = src.resize((GIF_WIDTH, GIF_HEIGHT), Image.LANCZOS)

        frames: list[Image.Image] = []
        for i in range(FRAMES):
            t = i / (FRAMES - 1)  # 0.0 -> 1.0
            zoom = ZOOM_START + (ZOOM_END - ZOOM_START) * t

            new_w = int(GIF_WIDTH * zoom)
            new_h = int(GIF_HEIGHT * zoom)
            zoomed = src.resize((new_w, new_h), Image.LANCZOS)

            # Crop back to target size (centre crop)
            left = (new_w - GIF_WIDTH) // 2
            top = (new_h - GIF_HEIGHT) // 2
            frame = zoomed.crop((left, top, left + GIF_WIDTH, top + GIF_HEIGHT))
            frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=128))

        buf = io.BytesIO()
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            loop=0,
            duration=FRAME_DURATION,
            optimize=False,
        )
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/gif;base64,{encoded}"
    except Exception:
        return None


async def generate_gif(image_url: str) -> str | None:
    """
    Download image from URL and return a base64 GIF data URI.
    Returns None silently on any failure.
    """
    if not image_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(image_url, follow_redirects=True)
            resp.raise_for_status()
            image_bytes = resp.content
    except Exception:
        return None

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _generate_ken_burns, image_bytes)

    await log_agent(
        "animator",
        "gif_generated" if result else "gif_failed",
        f"url={image_url[:80]}",
        f"ok={result is not None}",
    )
    return result


async def run_animator(state: dict) -> dict:
    """LangGraph-compatible node (unused in main flow but available)."""
    image_url = state.get("image_url")
    gif = await generate_gif(image_url)
    return {**state, "base64_gif": gif}
