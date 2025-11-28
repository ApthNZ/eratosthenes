from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.sql import func
from models.database import Base

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True)
    run_date = Column(Date, unique=True, nullable=False)
    feeds_processed = Column(Integer)
    items_fetched = Column(Integer)
    items_relevant = Column(Integer)
    items_priority_suggested = Column(Integer)
    api_calls_made = Column(Integer)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    status = Column(String(20))  # 'success', 'failed', 'running'
    error_message = Column(String(500))
    
    def __repr__(self):
        return f"<ProcessingLog(run_date={self.run_date}, status='{self.status}')>"
