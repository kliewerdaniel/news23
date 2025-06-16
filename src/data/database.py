import sqlite3
from datetime import datetime, timedelta
import logging

class NewsDatabase:
    def __init__(self, db_path: str = "news_cache.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.setup_database()

    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                content_hash TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def is_duplicate(self, content_hash: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT 1 FROM articles WHERE content_hash = ? AND processed_at > ?",
            (content_hash, datetime.now() - timedelta(days=3))
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def cache_article(self, content_hash: str):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO articles (id, content_hash) VALUES (?, ?)",
                (content_hash, content_hash)
            )
            conn.commit()
        except Exception as e:
            self.logger.error(f"Cache error: {e}")
        finally:
            conn.close()
