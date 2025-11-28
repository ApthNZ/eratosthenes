import aiohttp
import feedparser
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urlparse
import asyncio

from models.feed_source import FeedSource
from models.feed_item import FeedItem

logger = logging.getLogger(__name__)

class FeedFetcher:
    """Service for fetching and parsing RSS feeds."""
    
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def fetch_feed(self, feed_source: FeedSource) -> List[Dict]:
        """Fetch and parse a single RSS feed."""
        if not self.session:
            raise RuntimeError("FeedFetcher must be used as async context manager")
        
        try:
            logger.info(f"Fetching feed: {feed_source.name}")
            
            # Validate URL
            parsed_url = urlparse(feed_source.feed_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid feed URL: {feed_source.feed_url}")
            
            # Fetch feed content
            headers = {
                'User-Agent': 'Eratosthenes/1.0.0 RSS Aggregator for SOC'
            }
            
            async with self.session.get(feed_source.feed_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"HTTP {response.status} for feed {feed_source.name}")
                    return []
                
                content = await response.text()
            
            # Parse feed
            parsed_feed = feedparser.parse(content)
            
            if parsed_feed.bozo and parsed_feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {feed_source.name}: {parsed_feed.bozo_exception}")
            
            # Extract items
            items = []
            for entry in parsed_feed.entries[:50]:  # Limit to 50 items per feed
                try:
                    item_data = self._extract_item_data(entry, feed_source.id)
                    if item_data:
                        items.append(item_data)
                except Exception as e:
                    logger.error(f"Error extracting item from {feed_source.name}: {e}")
                    continue
            
            logger.info(f"Extracted {len(items)} items from {feed_source.name}")
            return items
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching feed: {feed_source.name}")
            return []
        except Exception as e:
            logger.error(f"Error fetching feed {feed_source.name}: {e}")
            return []
    
    def _extract_item_data(self, entry, source_feed_id: int) -> Optional[Dict]:
        """Extract data from a feed entry."""
        # Get URL
        url = getattr(entry, 'link', None)
        if not url:
            return None
        
        # Get title
        title = getattr(entry, 'title', 'Untitled')
        
        # Get content
        content = ''
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value
        elif hasattr(entry, 'description'):
            content = entry.description
        elif hasattr(entry, 'summary'):
            content = entry.summary
        
        # Get summary
        summary = getattr(entry, 'summary', content[:500] if content else '')
        
        # Get published date
        published_date = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
        
        if not published_date and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                published_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
        
        if not published_date:
            published_date = datetime.now(timezone.utc)
        
        return {
            'url': url,
            'title': title[:1000],  # Truncate long titles
            'content': content[:10000] if content else None,  # Truncate long content
            'summary': summary[:2000] if summary else None,  # Truncate long summaries
            'published_date': published_date,
            'source_feed_id': source_feed_id
        }
    
    async def fetch_all_feeds(self, feed_sources: List[FeedSource]) -> List[Dict]:
        """Fetch all feeds concurrently."""
        if not self.session:
            raise RuntimeError("FeedFetcher must be used as async context manager")
        
        tasks = [self.fetch_feed(feed_source) for feed_source in feed_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_items = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching feed {feed_sources[i].name}: {result}")
            else:
                all_items.extend(result)
        
        return all_items
