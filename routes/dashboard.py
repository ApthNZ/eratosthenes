from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from datetime import datetime, timedelta

from models.database import async_session_maker
from models.feed_item import FeedItem
from models.processing_log import ProcessingLog
from auth import verify_credentials

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = Depends(verify_credentials)):
    """Dashboard homepage with processing stats."""
    async with async_session_maker() as session:
        # Get today's date
        today = datetime.utcnow().date()
        
        # Get today's processing log
        result = await session.execute(
            select(ProcessingLog).where(ProcessingLog.run_date == today)
        )
        today_log = result.scalar_one_or_none()
        
        # Get pending review count
        result = await session.execute(
            select(func.count()).select_from(FeedItem).where(
                FeedItem.is_priority_suggestion == True,
                FeedItem.priority_feedback == None
            )
        )
        pending_count = result.scalar()
        
        # Get recent logs
        result = await session.execute(
            select(ProcessingLog).order_by(ProcessingLog.run_date.desc()).limit(7)
        )
        recent_logs = result.scalars().all()
        
        stats = {
            "today": {
                "feeds_processed": today_log.feeds_processed if today_log else 0,
                "items_fetched": today_log.items_fetched if today_log else 0,
                "items_relevant": today_log.items_relevant if today_log else 0,
                "items_priority_suggested": today_log.items_priority_suggested if today_log else 0,
            },
            "pending_review": pending_count,
            "recent_logs": recent_logs
        }
        
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "stats": stats}
        )
