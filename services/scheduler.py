import logging
from datetime import datetime
from sqlalchemy import select

from models.database import async_session_maker
from models.processing_log import ProcessingLog
from models.feed_source import FeedSource
from models.feed_item import FeedItem
from services.feed_fetcher import FeedFetcher
from services.claude_filter import ClaudeFilter

logger = logging.getLogger(__name__)

class ProcessingService:
    """Service for processing RSS feeds daily."""

    @staticmethod
    async def run_daily_processing(limit_feeds: int = None, limit_items_per_feed: int = 10):
        """
        Run daily feed processing job.

        Args:
            limit_feeds: Limit number of feeds to process (for testing)
            limit_items_per_feed: Limit items per feed (default: 10)

        This is the main entry point called by APScheduler.
        Processes all RSS feeds, filters with Claude, and generates output feeds.
        """
        logger.info("=" * 70)
        logger.info(f"Starting feed processing at {datetime.utcnow()}")
        logger.info("=" * 70)

        async with async_session_maker() as session:
            today = datetime.utcnow().date()

            # Create processing log entry
            log = ProcessingLog(
                run_date=today,
                started_at=datetime.utcnow(),
                status='running',
                feeds_processed=0,
                items_fetched=0,
                items_relevant=0,
                items_priority_suggested=0,
                api_calls_made=0
            )
            session.add(log)
            await session.commit()

            try:
                # Get enabled feeds
                query = select(FeedSource).where(FeedSource.enabled == True)
                if limit_feeds:
                    query = query.limit(limit_feeds)

                result = await session.execute(query)
                feeds = result.scalars().all()

                logger.info(f"Processing {len(feeds)} feeds...")

                # Initialize Claude filter
                claude_filter = ClaudeFilter()

                total_items_fetched = 0
                total_items_relevant = 0
                api_calls = 0

                # Process each feed
                for feed_source in feeds:
                    logger.info(f"Processing feed: {feed_source.name}")

                    # Fetch feed items
                    items = await FeedFetcher.fetch_feed(
                        feed_source.feed_url,
                        max_items=limit_items_per_feed
                    )
                    total_items_fetched += len(items)

                    if not items:
                        continue

                    # Filter for relevance with Claude (Pass 1)
                    logger.info(f"Filtering {len(items)} items for relevance...")
                    filtered_items = await claude_filter.filter_relevance(items)
                    api_calls += (len(items) + 9) // 10  # Batch size of 10

                    # Save relevant items to database
                    for item_data in filtered_items:
                        if not item_data.get('is_relevant'):
                            continue

                        # Check if item already exists
                        result = await session.execute(
                            select(FeedItem).where(FeedItem.url == item_data['url'])
                        )
                        existing = result.scalar_one_or_none()

                        if not existing:
                            # Create new feed item
                            feed_item = FeedItem(
                                url=item_data['url'],
                                title=item_data['title'],
                                content=item_data.get('content', ''),
                                summary=item_data.get('summary', ''),
                                published_date=item_data.get('published_date'),
                                source_feed_id=feed_source.id,
                                is_relevant=True,
                                processed_at=datetime.utcnow()
                            )
                            session.add(feed_item)
                            total_items_relevant += 1

                    # Update feed last_fetched
                    feed_source.last_fetched = datetime.utcnow()

                    await session.commit()
                    logger.info(f"✓ Processed {feed_source.name}")

                # Update processing log
                log.feeds_processed = len(feeds)
                log.items_fetched = total_items_fetched
                log.items_relevant = total_items_relevant
                log.api_calls_made = api_calls
                log.status = 'success'
                log.completed_at = datetime.utcnow()
                await session.commit()

                logger.info("=" * 70)
                logger.info(f"✓ Processing complete!")
                logger.info(f"  Feeds processed: {len(feeds)}")
                logger.info(f"  Items fetched: {total_items_fetched}")
                logger.info(f"  Items relevant: {total_items_relevant}")
                logger.info(f"  API calls made: {api_calls}")
                logger.info("=" * 70)

            except Exception as e:
                logger.error(f"Processing failed: {e}", exc_info=True)
                log.status = 'failed'
                log.completed_at = datetime.utcnow()
                await session.commit()
                raise
