#!/usr/bin/env python3
"""
Import RSS feeds from OPML file into Eratosthenes database.

Usage:
    python3 import_feeds.py [--opml-file seeds/feeds.opml]
"""
import asyncio
import argparse
import xml.etree.ElementTree as ET
import os
import sys
from sqlalchemy import select
from models.database import async_session_maker
from models.feed_source import FeedSource


async def parse_opml(opml_file):
    """Parse OPML file and extract feed URLs and names."""
    feeds = []
    
    tree = ET.parse(opml_file)
    root = tree.getroot()
    
    # Find all outline elements that have xmlUrl attribute (actual feeds)
    for outline in root.findall('.//outline[@xmlUrl]'):
        feed_url = outline.get('xmlUrl')
        name = outline.get('title') or outline.get('text')
        
        if feed_url and name:
            feeds.append({
                'feed_url': feed_url,
                'name': name
            })
    
    return feeds


async def import_feeds(opml_file):
    """Import feeds from OPML file into database."""
    print(f"📖 Reading OPML file: {opml_file}")
    
    # Parse OPML
    feeds = await parse_opml(opml_file)
    print(f"✅ Found {len(feeds)} feeds in OPML file")
    
    # Import into database
    async with async_session_maker() as session:
        imported_count = 0
        skipped_count = 0
        
        for feed_data in feeds:
            # Check if feed already exists
            result = await session.execute(
                select(FeedSource).where(FeedSource.feed_url == feed_data['feed_url'])
            )
            existing_feed = result.scalar_one_or_none()
            
            if existing_feed:
                print(f"⏭️  Skipped (already exists): {feed_data['name']}")
                skipped_count += 1
            else:
                # Create new feed source
                feed_source = FeedSource(
                    feed_url=feed_data['feed_url'],
                    name=feed_data['name'],
                    enabled=True
                )
                session.add(feed_source)
                print(f"✅ Imported: {feed_data['name']}")
                imported_count += 1
        
        # Commit all changes
        await session.commit()
    
    print(f"\n📊 Import Summary:")
    print(f"   • Imported: {imported_count} feeds")
    print(f"   • Skipped:  {skipped_count} feeds")
    print(f"   • Total:    {len(feeds)} feeds")


async def list_feeds():
    """List all feeds in the database."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(FeedSource).order_by(FeedSource.name)
        )
        feeds = result.scalars().all()
        
        print(f"\n📋 Current Feed Sources ({len(feeds)} total):\n")
        for feed in feeds:
            status = "✅" if feed.enabled else "❌"
            print(f"{status} {feed.name}")
            print(f"   {feed.feed_url}")
            if feed.last_fetched:
                print(f"   Last fetched: {feed.last_fetched}")
            print()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Import RSS feeds from OPML file into Eratosthenes'
    )
    parser.add_argument(
        '--opml-file',
        default='seeds/feeds.opml',
        help='Path to OPML file (default: seeds/feeds.opml)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all feeds in database instead of importing'
    )
    
    args = parser.parse_args()
    
    if args.list:
        await list_feeds()
    else:
        if not os.path.exists(args.opml_file):
            print(f"❌ Error: OPML file not found: {args.opml_file}")
            sys.exit(1)
        
        await import_feeds(args.opml_file)
        print("\n✅ Feed import complete!")


if __name__ == '__main__':
    asyncio.run(main())
