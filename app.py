import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from models.database import init_db, get_db_session
from routes.dashboard import router as dashboard_router
from routes.review import router as review_router
from routes.feeds import router as feeds_router
from routes.api import router as api_router
from services.scheduler import ProcessingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown tasks."""
    # Startup
    logger.info("Starting Eratosthenes RSS aggregator...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start scheduler
    nz_tz = pytz.timezone('Pacific/Auckland')
    scheduler.add_job(
        ProcessingService.run_daily_processing,
        CronTrigger(hour=6, minute=0, timezone=nz_tz),
        id='daily_processing',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started - daily processing at 6:00 AM NZST")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Eratosthenes",
    description="RSS feed aggregator and intelligent filter for SOC analysts",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(dashboard_router)
app.include_router(review_router)
app.include_router(feeds_router)
app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint for Render deployment."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
