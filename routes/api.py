from fastapi import APIRouter
from sqlalchemy import select, func
from datetime import datetime

from models.database import get_db_session
from models.feed_item import FeedItem
from models.processing_log import ProcessingLog

router = APIRouter()

@router.get("/stats")
async def get_stats():
    """JSON endpoint for processing statistics."""
    async with get_db_session() as session:
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
