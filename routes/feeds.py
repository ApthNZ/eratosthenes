from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from feedgen.feed import FeedGenerator

from models.database import async_session_maker
from models.feed_item import FeedItem

router = APIRouter()

@router.get("/feeds/standard.xml")
async def standard_feed():
    """Standard RSS feed (all relevant items)."""
    async with async_session_maker() as session:
        # Get relevant items from last 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        result = await session.execute(
            select(FeedItem)
            .where(
                FeedItem.is_relevant == True,
                FeedItem.published_date >= cutoff_date
            )
            .order_by(FeedItem.published_date.desc())
            .limit(100)
        )
        items = result.scalars().all()
        
        # Generate RSS feed
        fg = FeedGenerator()
        fg.id('https://eratosthenes.onrender.com/feeds/standard.xml')
        fg.title('Eratosthenes - InfoSec News (All Relevant)')
        fg.description('Curated InfoSec news filtered by Claude AI')
        fg.link(href='https://eratosthenes.onrender.com', rel='alternate')
        fg.language('en')
        
        for item in items:
            fe = fg.add_entry()
            fe.id(item.url)
            fe.title(item.title)
            fe.link(href=item.url)
            fe.description(item.summary or item.content or '')
            # Make datetime timezone-aware (UTC)
            pub_date = item.published_date.replace(tzinfo=timezone.utc) if item.published_date else datetime.now(timezone.utc)
            fe.pubDate(pub_date)
        
        rss_str = fg.rss_str(pretty=True)
        return Response(content=rss_str, media_type="application/rss+xml")

@router.get("/feeds/priority.xml")
async def priority_feed():
    """Priority RSS feed (approved items only)."""
    async with async_session_maker() as session:
        # Get approved priority items from last 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        result = await session.execute(
            select(FeedItem)
            .where(
                FeedItem.is_priority_approved == True,
                FeedItem.published_date >= cutoff_date
            )
            .order_by(FeedItem.published_date.desc())
            .limit(100)
        )
        items = result.scalars().all()
        
        # Generate RSS feed
        fg = FeedGenerator()
        fg.id('https://eratosthenes.onrender.com/feeds/priority.xml')
        fg.title('Eratosthenes - InfoSec News (Priority)')
        fg.description('High-priority InfoSec news approved by SOC analysts')
        fg.link(href='https://eratosthenes.onrender.com', rel='alternate')
        fg.language('en')
        
        for item in items:
            fe = fg.add_entry()
            fe.id(item.url)
            fe.title(item.title)
            fe.link(href=item.url)
            fe.description(item.summary or item.content or '')
            # Make datetime timezone-aware (UTC)
            pub_date = item.published_date.replace(tzinfo=timezone.utc) if item.published_date else datetime.now(timezone.utc)
            fe.pubDate(pub_date)
        
        rss_str = fg.rss_str(pretty=True)
        return Response(content=rss_str, media_type="application/rss+xml")
