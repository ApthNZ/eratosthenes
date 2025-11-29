from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, update
from datetime import datetime

from models.database import async_session_maker
from models.feed_item import FeedItem
from auth import verify_credentials

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/review", response_class=HTMLResponse)
async def review_queue(request: Request, page: int = 1, limit: int = 20, username: str = Depends(verify_credentials)):
    """Priority review queue interface."""
    async with async_session_maker() as session:
        # Get pending priority suggestions
        offset = (page - 1) * limit
        result = await session.execute(
            select(FeedItem)
            .where(
                FeedItem.is_priority_suggestion == True,
                FeedItem.priority_feedback == None
            )
            .order_by(FeedItem.published_date.desc())
            .offset(offset)
            .limit(limit)
        )
        items = result.scalars().all()
        
        return templates.TemplateResponse(
            "review.html",
            {
                "request": request,
                "items": items,
                "page": page,
                "limit": limit
            }
        )

@router.post("/review/{item_id}/approve")
async def approve_priority(item_id: int, username: str = Depends(verify_credentials)):
    """Approve a priority suggestion."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(FeedItem).where(FeedItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Update item
        item.priority_feedback = True
        item.is_priority_approved = True
        item.reviewed_at = datetime.utcnow()
        
        await session.commit()
        
        return JSONResponse({"status": "approved", "item_id": item_id})

@router.post("/review/{item_id}/reject")
async def reject_priority(item_id: int, username: str = Depends(verify_credentials)):
    """Reject a priority suggestion."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(FeedItem).where(FeedItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Update item
        item.priority_feedback = False
        item.is_priority_approved = False
        item.reviewed_at = datetime.utcnow()
        
        await session.commit()
        
        return JSONResponse({"status": "rejected", "item_id": item_id})
