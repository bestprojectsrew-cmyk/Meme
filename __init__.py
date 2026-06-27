"""
MemePulse AI - Main Application
SRS Reference: Part 3 (System Architecture), Part 5 (Frontend/Dashboard)

Single FastAPI app serving:
- The review dashboard (HTML, server-rendered with Jinja2 - simplest possible frontend)
- API endpoints to generate new memes and approve/reject them
- Static file serving for generated meme images

Run locally:
    uvicorn app.main:app --reload

Deployed: Railway runs this same command automatically (see Procfile).
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import database
from app.trends.reddit_source import collect_trends, deduplicate_trends
from app.ai.caption_ai import generate_meme_ideas
from app.render.meme_renderer import render_meme
from app.safety_filter import filter_safe_ideas
from app.instagram_publisher import publish_meme_to_instagram

app = FastAPI(title="MemePulse AI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.on_event("startup")
def on_startup():
    """SRS Part 3 Sec 33: Initialization - ensure DB schema exists before serving requests."""
    database.init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """
    Main review dashboard. SRS Part 1 Sec 8: 'Human approves/edits before posting' workflow.
    Shows pending memes for review, plus recently approved/posted ones.
    """
    pending = database.get_memes(status="pending", limit=20)
    approved = database.get_memes(status="approved", limit=10)
    stats = database.get_stats()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "pending": pending,
            "approved": approved,
            "stats": stats,
        },
    )


@app.post("/generate")
def generate_new_memes(count: int = 3):
    """
    Triggers the pipeline: fetch trends -> generate AI captions -> render images -> save to DB.
    SRS Part 1 Sec 8 System Workflow, steps 1-7 (everything before Safety Filter/Publish).
    """
    trends = collect_trends()
    trends = deduplicate_trends(trends)

    if not trends:
        raise HTTPException(
            status_code=503,
            detail="Could not fetch trends right now. Reddit may be temporarily unreachable - try again shortly.",
        )

    trends.sort(key=lambda t: t.velocity_score, reverse=True)
    top_trends = trends[:count]

    created_ids = []

    for trend in top_trends:
        try:
            ideas = generate_meme_ideas(
                trend_title=trend.title,
                trend_category=trend.category,
                n=2,
            )
        except RuntimeError as e:
            # Missing API key - surface clearly rather than failing silently
            raise HTTPException(status_code=500, detail=str(e))

        if not ideas:
            continue

        # SRS Part 3 Sec 47: Safety Filter runs before anything reaches the human reviewer.
        ideas = filter_safe_ideas(ideas)
        if not ideas:
            continue

        best_idea = ideas[0]

        filename = f"meme_{uuid.uuid4().hex[:10]}.png"
        image_path = os.path.join(STATIC_DIR, filename)

        render_meme(
            caption_top=best_idea.caption_top,
            caption_bottom=best_idea.caption_bottom,
            output_path=image_path,
        )

        meme_id = database.insert_meme(
            trend_title=trend.title,
            trend_category=trend.category,
            trend_url=trend.url,
            caption_top=best_idea.caption_top,
            caption_bottom=best_idea.caption_bottom,
            humor_style=best_idea.humor_style,
            confidence_score=best_idea.confidence_score,
            originality_score=best_idea.originality_score,
            image_path=f"/static/{filename}",
        )
        created_ids.append(meme_id)

    return RedirectResponse(url="/", status_code=303)


@app.post("/memes/{meme_id}/approve")
def approve_meme(meme_id: int):
    """SRS Part 1 Sec 8: human-in-the-loop approval before any post goes live."""
    meme = database.get_meme_by_id(meme_id)
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")

    database.update_meme_status(meme_id, "approved")
    return RedirectResponse(url="/", status_code=303)


@app.post("/memes/{meme_id}/reject")
def reject_meme(meme_id: int):
    meme = database.get_meme_by_id(meme_id)
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")

    database.update_meme_status(meme_id, "rejected")
    return RedirectResponse(url="/", status_code=303)


@app.post("/memes/{meme_id}/post")
def post_to_instagram(meme_id: int, request: Request):
    """
    SRS Part 3 Sec 48: Instagram Integration - publishes an approved meme live.
    Requires IG_ACCESS_TOKEN and IG_BUSINESS_ACCOUNT_ID to be configured (Phase 2 setup).
    """
    meme = database.get_meme_by_id(meme_id)
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")

    if meme["status"] != "approved":
        raise HTTPException(status_code=400, detail="Only approved memes can be posted")

    # Build the full public URL to the image, since Meta fetches images server-side via URL
    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}{meme['image_path']}"

    caption_text = f"{meme['caption_top']}\n\n{meme['caption_bottom']}".strip()

    result = publish_meme_to_instagram(image_url=image_url, caption=caption_text)

    if not result.success:
        raise HTTPException(status_code=502, detail=f"Instagram publish failed: {result.error}")

    database.mark_posted(meme_id, instagram_post_id=result.post_id or "")
    return RedirectResponse(url="/", status_code=303)


@app.get("/health")
def health_check():
    """Used by Railway/hosting platforms to confirm the app is alive."""
    return {"status": "ok"}
