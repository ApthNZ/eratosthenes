"""RSS feed fetching and parsing service."""
import logging
import feedparser
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FeedFetcher:
    """Fetch and parse RSS feeds."""

    @staticmethod
    async def fetch_feed(feed_url: str, max_items: int = 50) -> List[Dict]:
        """Fetch and parse a single RSS feed.
        
        Args:
            feed_url: URL of the RSS feed
            max_items: Maximum number of items to return
            
        Returns:
            List of feed items with normalized fields
        """
        try:
            # Parse feed (feedparser handles various formats)
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                # Feed has parsing errors
                logger.warning(f"Feed parsing errors for {feed_url}: {feed.bozo_exception}")

            items = []
            for entry in feed.entries[:max_items]:
                # Extract fields with fallbacks
                item = {
                    'url': entry.get('link', ''),
                    'title': entry.get('title', 'No title'),
                    'content': FeedFetcher._extract_content(entry),
                    'summary': entry.get('summary', ''),
                    'published_date': FeedFetcher._parse_date(entry)
                }

                # Only include items with a URL
                if item['url']:
                    items.append(item)

            logger.info(f"Fetched {len(items)} items from {feed_url}")
            return items

        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_url}: {e}")
            return []

    @staticmethod
    def _extract_content(entry) -> str:
        """Extract content from feed entry, trying various fields."""
        # Try content field first
        if hasattr(entry, 'content') and entry.content:
            return entry.content[0].get('value', '')

        # Try description
        if hasattr(entry, 'description'):
            return entry.description

        # Fall back to summary
        if hasattr(entry, 'summary'):
            return entry.summary

        return ''

    @staticmethod
    def _parse_date(entry) -> Optional[datetime]:
        """Parse published date from feed entry."""
        # Try published_parsed
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except Exception:
                pass

        # Try updated_parsed
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except Exception:
                pass

        # Default to now
        return datetime.utcnow()
