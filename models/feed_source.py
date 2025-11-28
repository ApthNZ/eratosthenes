from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base

class FeedSource(Base):
    __tablename__ = "feed_sources"
    
    id = Column(Integer, primary_key=True)
    feed_url = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    last_fetched = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    feed_items = relationship("FeedItem", back_populates="source_feed")
    
    def __repr__(self):
        return f"<FeedSource(id={self.id}, name='{self.name}', enabled={self.enabled})>"
