from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Article:
    title: str
    content: str
    url: str
    published: datetime
    source: str
    summary: str = ""
    sentiment_score: float = 0.0
    importance_score: float = 0.0
    relevancy_score: float = 0.0
    cluster_id: int = -1

@dataclass
class BroadcastSegment:
    topic: str
    content: str
    articles: List[Article]
    importance: float
