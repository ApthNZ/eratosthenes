from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base

class FeedItem(Base):
    __tablename__ = "feed_items"
    
    id = Column(Integer, primary_key=True)
    url = Column(Text, unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text)
    summary = Column(Text)
    published_date = Column(DateTime, index=True)
    source_feed_id = Column(Integer, ForeignKey("feed_sources.id"))
    
    # Processing results
    is_relevant = Column(Boolean, index=True)
    is_priority_suggestion = Column(Boolean, default=False)
    is_priority_approved = Column(Boolean, default=False)
    priority_feedback = Column(Boolean, index=True)  # true=approved, false=rejected, null=pending
    
    # AI reasoning
    relevance_reasoning = Column(Text)
    priority_reasoning = Column(Text)
    priority_confidence = Column(String(10))  # high/medium/low
    matched_criteria = Column(Text)  # JSON string of matched criteria
    
    # Metadata
    processed_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    source_feed = relationship("FeedSource", back_populates="feed_items")
    
    def __repr__(self):
        return f"<FeedItem(id={self.id}, title='{self.title[:50]}...', is_relevant={self.is_relevant})>"
