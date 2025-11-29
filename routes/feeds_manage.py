from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from models.database import async_session_maker
from models.feed_source import FeedSource
from auth import verify_credentials

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/feeds-manage", response_class=HTMLResponse)
async def manage_feeds(request: Request, username: str = Depends(verify_credentials)):
    """Feed management interface."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(FeedSource).order_by(FeedSource.name)
        )
        feeds = result.scalars().all()

        return templates.TemplateResponse(
            "feeds_manage.html",
            {
                "request": request,
                "feeds": feeds,
                "total_feeds": len(feeds)
            }
        )
