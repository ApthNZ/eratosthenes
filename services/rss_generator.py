import logging
from datetime import datetime, timedelta
from typing import List
from feedgen.feed import FeedGenerator

from models.feed_item import FeedItem

logger = logging.getLogger(__name__)

class RSSGenerator:
    """Service for generating RSS feeds."""
    
    def __init__(self):
        self.base_url = "https://eratosthenes.onrender.com"  # Update with actual domain
    
    def generate_standard_feed(self, items: List[FeedItem]) -> str:
        """Generate standard RSS feed with all relevant items."""
        fg = self._create_base_feed(
            title="Eratosthenes - Security News (All Relevant)",
            description="Curated security news filtered for InfoSec relevance",
            link=f"{self.base_url}/feeds/standard.xml"
        )
        
        for item in items:
            fe = fg.add_entry()
            fe.id(item.url)
            fe.title(item.title)
            fe.link(href=item.url)
            fe.description(item.summary or item.content or "No description available")
            fe.pubDate(item.published_date)
            fe.author(name=item.source_feed.name if item.source_feed else "Unknown")
        
        return fg.rss_str(pretty=True).decode('utf-8')
    
    def generate_priority_feed(self, items: List[FeedItem]) -> str:
        """Generate priority RSS feed with only approved priority items."""
        fg = self._create_base_feed(
            title="Eratosthenes - Priority Security News",
            description="High-priority security news requiring immediate SOC attention",
            link=f"{self.base_url}/feeds/priority.xml"
        )
        
        for item in items:
            fe = fg.add_entry()
            fe.id(item.url)
            fe.title(f"[PRIORITY] {item.title}")
            
            # Add priority reasoning to description
            description = item.summary or item.content or "No description available"
            if item.priority_reasoning:
                description += f"\n\n[Priority Reasoning: {item.priority_reasoning}]"
            
            fe.link(href=item.url)
            fe.description(description)
            fe.pubDate(item.published_date)
            fe.author(name=item.source_feed.name if item.source_feed else "Unknown")
        
        return fg.rss_str(pretty=True).decode('utf-8')
    
    def _create_base_feed(self, title: str, description: str, link: str) -> FeedGenerator:
        """Create base RSS feed with common metadata."""
        fg = FeedGenerator()
        fg.title(title)
        fg.description(description)
        fg.link(href=link, rel='alternate')
        fg.language('en')
        fg.generator('Eratosthenes 1.0.0')
        fg.managingEditor('hecate2104@proton.me (ApthNZ)')
        fg.webMaster('hecate2104@proton.me (ApthNZ)')
        fg.lastBuildDate(datetime.now())
        fg.ttl(60)  # 1 hour TTL
        
        return fg
