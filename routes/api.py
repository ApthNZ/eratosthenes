from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from datetime import datetime
import xml.etree.ElementTree as ET
import os

from models.database import async_session_maker
from models.feed_item import FeedItem
from models.feed_source import FeedSource
from models.processing_log import ProcessingLog

router = APIRouter()

@router.get("/stats")
async def get_stats():
    """JSON endpoint for processing statistics."""
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
        
        # Get total training examples (approved or rejected)
        result = await session.execute(
            select(func.count()).select_from(FeedItem).where(
                FeedItem.priority_feedback != None
            )
        )
        training_count = result.scalar()
        
        stats = {
            "today": {
                "feeds_processed": today_log.feeds_processed if today_log else 0,
                "items_fetched": today_log.items_fetched if today_log else 0,
                "items_relevant": today_log.items_relevant if today_log else 0,
                "items_priority_suggested": today_log.items_priority_suggested if today_log else 0,
                "api_calls_made": today_log.api_calls_made if today_log else 0
            },
            "pending_review": pending_count,
            "total_training_examples": training_count
        }
        
        return stats


@router.post("/import-feeds")
async def import_feeds_from_opml():
    """Import RSS feeds from OPML file into database."""
    opml_file = "seeds/feeds.opml"
    
    if not os.path.exists(opml_file):
        raise HTTPException(status_code=404, detail=f"OPML file not found: {opml_file}")
    
    # Parse OPML
    feeds = []
    tree = ET.parse(opml_file)
    root = tree.getroot()
    
    # Find all outline elements that have xmlUrl attribute (actual feeds)
    for outline in root.findall('.//outline[@xmlUrl]'):
        feed_url = outline.get('xmlUrl')
        name = outline.get('title') or outline.get('text')
        
        if feed_url and name:
            feeds.append({
                'feed_url': feed_url,
                'name': name
            })
    
    # Import into database
    async with async_session_maker() as session:
        imported_count = 0
        skipped_count = 0
        
        for feed_data in feeds:
            # Check if feed already exists
            result = await session.execute(
                select(FeedSource).where(FeedSource.feed_url == feed_data['feed_url'])
            )
            existing_feed = result.scalar_one_or_none()
            
            if not existing_feed:
                # Create new feed source
                feed_source = FeedSource(
                    feed_url=feed_data['feed_url'],
                    name=feed_data['name'],
                    enabled=True
                )
                session.add(feed_source)
                imported_count += 1
            else:
                skipped_count += 1
        
        # Commit all changes
        await session.commit()
    
    return JSONResponse({
        "status": "success",
        "message": f"Imported {imported_count} feeds, skipped {skipped_count} (already existed)",
        "imported": imported_count,
        "skipped": skipped_count,
        "total": len(feeds)
    })


@router.get("/feeds")
async def list_feeds():
    """List all feed sources in the database."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(FeedSource).order_by(FeedSource.name)
        )
        feeds = result.scalars().all()
        
        feed_list = []
        for feed in feeds:
            feed_list.append({
                "id": feed.id,
                "name": feed.name,
                "feed_url": feed.feed_url,
                "enabled": feed.enabled,
                "last_fetched": feed.last_fetched.isoformat() if feed.last_fetched else None,
                "created_at": feed.created_at.isoformat() if feed.created_at else None
            })
        
        return {
            "total": len(feed_list),
            "feeds": feed_list
        }


@router.post("/process-feeds")
async def process_feeds_manually(limit_feeds: int = 5, limit_items: int = 5):
    """
    Manually trigger feed processing (for testing).
    
    Args:
        limit_feeds: Number of feeds to process (default: 5 for testing)
        limit_items: Items per feed (default: 5 for testing)
    """
    from services.scheduler import ProcessingService
    
    try:
        await ProcessingService.run_daily_processing(
            limit_feeds=limit_feeds,
            limit_items_per_feed=limit_items
        )
        
        return JSONResponse({
            "status": "success",
            "message": f"Processed up to {limit_feeds} feeds with {limit_items} items each"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
