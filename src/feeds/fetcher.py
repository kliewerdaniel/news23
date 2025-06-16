import asyncio
import aiohttp
import feedparser
import yaml
import re
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from src.core.config import CONFIG
from src.core.models import Article
from src.data.database import NewsDatabase

class FeedFetcher:
    def __init__(self, feeds_file: str = "feeds.yaml"):
        self.feeds_file = feeds_file
        self.db = NewsDatabase()
        self.logger = logging.getLogger(__name__)

    async def fetch_feeds_batch(self, batch_size: int = 5) -> List[Article]:
        """Optimized batch processing of feeds"""
        with open(self.feeds_file, 'r') as f:
            feeds_config = yaml.safe_load(f)

        feeds = feeds_config.get('feeds', [])
        articles = []

        for i in range(0, len(feeds), batch_size):
            batch = feeds[i:i+batch_size]
            async with aiohttp.ClientSession() as session:
                tasks = [self.fetch_single_feed(session, feed) for feed in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, list):
                        articles.extend(result)

            if i + batch_size < len(feeds):
                await asyncio.sleep(0.5)

        return articles

    async def fetch_single_feed(self, session: aiohttp.ClientSession, feed_url: str) -> List[Article]:
        """Streamlined feed fetching"""
        self.logger.info(f"Attempting to fetch feed: {feed_url}")
        try:
            async with session.get(feed_url, timeout=60) as response:
                response.raise_for_status()
                content = await response.text()

            feed = feedparser.parse(content)
            articles = []

            fetched_count = 0
            for entry in feed.entries:
                if fetched_count >= CONFIG["processing"]["max_articles_per_feed"]:
                    break

                content = self.extract_content(entry)
                if len(content) < CONFIG["processing"]["min_article_length"]:
                    self.logger.debug(f"Skipping article due to short length: {entry.get('title', 'No Title')}")
                    continue

                content_hash = hashlib.md5(content.encode()).hexdigest()
                if self.db.is_duplicate(content_hash):
                    self.logger.debug(f"Skipping duplicate article: {entry.get('title', 'No Title')}")
                    continue

                article = Article(
                    title=entry.get('title', ''),
                    content=content,
                    url=entry.get('link', ''),
                    published=self.parse_date(entry),
                    source=feed.feed.get('title', feed_url),
                )

                articles.append(article)
                self.db.cache_article(content_hash)
                fetched_count += 1

            self.logger.info(f"Successfully fetched {len(articles)} articles from {feed_url}")
            return articles

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP error fetching {feed_url}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"General error fetching or parsing {feed_url}: {e}")
            return []

    def extract_content(self, entry) -> str:
        """Extract and clean content"""
        content = ""
        for field in ['content', 'summary', 'description']:
            if hasattr(entry, field):
                if field == 'content' and entry.content:
                    content = entry.content[0].value if entry.content else ""
                else:
                    content = getattr(entry, field, "")
                break

        return re.sub(r'<[^>]+>', '', content).strip()

    def parse_date(self, entry) -> datetime:
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
        except:
            pass
        return datetime.now()
