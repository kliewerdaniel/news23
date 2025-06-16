import asyncio
import aiohttp
import logging
import re
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import importlib.util
import queue
import io

from src.core.config import CONFIG
from src.core.models import Article, BroadcastSegment
from src.core.circuit_breaker import CircuitBreaker
from src.core.performance_monitor import PerformanceMonitor
from src.data.database import NewsDatabase
from src.feeds.fetcher import FeedFetcher
from src.nlp.sentiment import SentimentAnalyzer
from src.nlp.clustering import StreamClusterer
from src.utils import load_persona # Import load_persona
from src.prompts import create_summary_prompt, create_segment_script_prompt, create_transition_phrase_prompt # Import prompt functions

edge_tts_available = importlib.util.find_spec("edge_tts") is not None
if edge_tts_available:
    import edge_tts

class NewsGenerator:
    def __init__(self, audio_queue: queue.Queue, feeds_file: str = "feeds.yaml", topic: Optional[str] = None, guidance: Optional[str] = None, persona_file: str = "personas/objective.yaml"):
        self.audio_queue = audio_queue
        self.feeds_file = feeds_file
        self.circuit_breaker = CircuitBreaker()
        self.performance_monitor = PerformanceMonitor()
        self.topic = topic
        self.guidance = guidance
        self.relevancy_threshold = CONFIG["relevancy"]["threshold"] # Use threshold from config
        self.logger = logging.getLogger(__name__)

        self.db = NewsDatabase()
        self.feed_fetcher = FeedFetcher(feeds_file=self.feeds_file)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.article_clusterer = StreamClusterer()
        self.persona = load_persona(persona_file) # Load persona here using the provided file
    async def process_articles_smart(self, articles: List[Article]) -> List[Article]:
        """Streamlined processing with circuit breaker"""
        if not articles:
            return []

        start_time = datetime.now()

        async with aiohttp.ClientSession() as session:
            self.article_clusterer.session = session # Pass the session to the clusterer
            self.article_clusterer.circuit_breaker = self.circuit_breaker # Pass the circuit breaker to the clusterer

            # Generate summaries
            summary_tasks = [self.generate_summary_safe(session, article) for article in articles]
            summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)

            for i, result in enumerate(summaries):
                if isinstance(result, Exception):
                    self.logger.error(f"Summary failed for {articles[i].title}: {result}")
                    articles[i].summary = articles[i].content[:150] + "..."
                else:
                    articles[i].summary = result

            # Calculate relevancy scores if a topic is provided
            if self.topic:
                relevancy_tasks = [self.calculate_relevancy_score(session, article) for article in articles]
                relevancy_scores = await asyncio.gather(*relevancy_tasks, return_exceptions=True)

                for i, result in enumerate(relevancy_scores):
                    if isinstance(result, Exception):
                        self.logger.error(f"Relevancy scoring failed for {articles[i].title}: {result}")
                        articles[i].relevancy_score = 0.0
                    else:
                        articles[i].relevancy_score = result

        # Cluster articles using StreamClusterer
        headlines = [article.title for article in articles]
        timestamp_source_info = [(article.published, article.source) for article in articles]
        
        cluster_results = await self.article_clusterer.process_batch(headlines, timestamp_source_info)

        # Assign cluster_id back to articles
        for cluster_id, cluster_data in cluster_results.items():
            for headline in cluster_data['headlines']:
                # Find the original article object and assign the cluster_id
                for article in articles:
                    if article.title == headline:
                        article.cluster_id = cluster_id
                        break

        # Calculate importance scores
        self.calculate_importance_scores(articles)

        duration = (datetime.now() - start_time).total_seconds()
        self.performance_monitor.track_operation("process_articles", duration)

        return articles

    async def generate_summary_safe(self, session: aiohttp.ClientSession, article: Article) -> str:
        """Safe summary generation with circuit breaker using aiohttp"""
        if not self.circuit_breaker.can_execute():
            return article.content[:150] + "..."

        prompt = create_summary_prompt(article.title, article.content, self.persona)

        try:
            async with session.post(
                f"{CONFIG['ollama_api']['base_url']}/api/generate",
                json={
                    'model': CONFIG["models"]["summary_model"],
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.3, 'max_tokens': 10000}
                },
                timeout=aiohttp.ClientTimeout(total=CONFIG["ollama_api"]["timeouts"]["summary"])
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self.circuit_breaker.record_success()
                return data['response'].strip()

        except aiohttp.ClientResponseError as e:
            error_detail = await e.response.text() if e.response else "No response body"
            self.logger.error(f"Summary LLM API error (status: {e.status}): {error_detail}")
            self.circuit_breaker.record_failure()
            return article.content[:150] + "..."
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during summary LLM call: {e}")
            self.circuit_breaker.record_failure()
            return article.content[:150] + "..."
        except Exception as e:
            self.logger.error(f"Unexpected error during summary LLM call: {e}")
            self.circuit_breaker.record_failure()
            return article.content[:150] + "..."

    async def calculate_relevancy_score(self, session: aiohttp.ClientSession, article: Article) -> float:
        """Calculate relevancy score using LLM with aiohttp"""
        if not self.topic or not self.circuit_breaker.can_execute():
            return 0.0

        prompt = f"""Given the topic: "{self.topic}"

        Score the following article from 0 to 10 on how relevant it is to the topic.
        Return only the score as a single number.

        Article Title: {article.title}
        Article Summary: {article.summary}
        """

        try:
            async with session.post(
                f"{CONFIG['ollama_api']['base_url']}/api/generate",
                json={
                    'model': CONFIG["models"]["summary_model"],
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.1, 'max_tokens': 5}
                },
                timeout=aiohttp.ClientTimeout(total=CONFIG["ollama_api"]["timeouts"]["relevancy"])
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self.circuit_breaker.record_success()
                score_str = data['response'].strip()
                try:
                    score = float(score_str)
                    return max(0.0, min(10.0, score))
                except ValueError:
                    self.logger.warning(f"LLM returned non-numeric relevancy score: '{score_str}'")
                    return 0.0

        except aiohttp.ClientResponseError as e:
            error_detail = await e.response.text() if e.response else "No response body"
            self.logger.error(f"Relevancy scoring LLM API error (status: {e.status}): {error_detail}")
            self.circuit_breaker.record_failure()
            return 0.0
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during relevancy scoring LLM call: {e}")
            self.circuit_breaker.record_failure()
            return 0.0
        except Exception as e:
            self.logger.error(f"Unexpected error during relevancy scoring LLM call: {e}")
            self.circuit_breaker.record_failure()
            return 0.0

    def calculate_importance_scores(self, articles: List[Article]):
        """Enhanced importance scoring"""
        for article in articles:
            hours_old = (datetime.now() - article.published).total_seconds() / 3600
            freshness = max(0, 1 - (hours_old / 48))

            content_quality = min(1.0, len(article.content) / 800)

            sentences = len(re.split(r'[.!?]+', article.content))
            words = len(article.content.split())
            readability = 1.0 if sentences == 0 else min(1.0, words / (sentences * 15))

            sentiment_impact = abs(self.sentiment_analyzer.get_sentiment_score(article.content))

            article.importance_score = (
                0.4 * freshness +
                0.3 * content_quality +
                0.2 * sentiment_impact +
                0.1 * readability
            )

    def create_broadcast_segments(self, articles: List[Article]) -> List[BroadcastSegment]:
        """Create segments from clustered articles"""
        segments = []
        clusters = {}

        if self.topic:
            articles = [a for a in articles if a.relevancy_score >= self.relevancy_threshold]
            self.logger.info(f"Filtered to {len(articles)} articles above relevancy threshold ({self.relevancy_threshold}) for topic '{self.topic}'")
            if not articles:
                self.logger.warning("No articles met the relevancy threshold for the given topic.")
                return []

        for article in articles:
            cluster_id = article.cluster_id
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(article)

        for cluster_id, cluster_articles in clusters.items():
            if not cluster_articles:
                continue

            cluster_articles.sort(key=lambda x: x.importance_score, reverse=True)
            topic = self.extract_topic(cluster_articles[:2])
            selected_articles = cluster_articles[:2]
            avg_importance = np.mean([a.importance_score for a in selected_articles])

            segment = BroadcastSegment(
                topic=topic,
                content="",
                articles=selected_articles,
                importance=avg_importance
            )
            segments.append(segment)

        segments.sort(key=lambda x: x.importance, reverse=True)
        return segments[:CONFIG["processing"]["target_segments"]]

    def extract_topic(self, articles: List[Article]) -> str:
        """Simple topic extraction"""
        if not articles:
            return "General News"

        if self.topic:
            return self.topic

        all_words = []
        for article in articles:
            words = re.findall(r'\b[A-Z][a-z]+\b', article.title)
            all_words.extend(words)

        if all_words:
            word_counts = {}
            for word in all_words:
                word_counts[word] = word_counts.get(word, 0) + 1
            return max(word_counts, key=word_counts.get)

        return articles[0].title.split()[:2]

    async def generate_and_queue_audio(self, script: str):
        """Generates audio from a script and puts it into the queue."""
        if not edge_tts_available:
            self.logger.error("Cannot generate audio: edge_tts library not found.")
            return

        try:
            self.logger.info("Generating audio for a new segment...")
            communicate = edge_tts.Communicate(script, "en-US-EricNeural")

            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_buffer.seek(0)
            self.audio_queue.put(audio_buffer.read())
            self.logger.info("Audio segment added to the playback queue.")

        except Exception as e:
            self.logger.error(f"Failed to generate or queue audio: {e}")

    async def generate_segment_script(self, segment: BroadcastSegment) -> str:
        """Generate segment script for a given topic and context."""
        context = "\n".join([f"{a.title}: {a.summary}" for a in segment.articles])
        prompt = create_segment_script_prompt(segment.topic, context, self.guidance, self.persona)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{CONFIG['ollama_api']['base_url']}/api/generate",
                    json={
                        'model': CONFIG["models"]["broadcast_model"],
                        'prompt': prompt,
                        'stream': False,
                        'options': {'temperature': 0.4, 'max_tokens': 30000}
                    },
                    timeout=aiohttp.ClientTimeout(total=CONFIG["ollama_api"]["timeouts"]["segment"])
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data['response'].strip()

        except aiohttp.ClientResponseError as e:
            error_detail = await e.response.text() if e.response else "No response body"
            self.logger.error(f"Script generation LLM API error (status: {e.status}): {error_detail}")
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during script generation LLM call: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during script generation LLM call: {e}")
        return "Failed to generate news segment."

    async def generate_transition_phrase(self, previous_topic: str, current_topic: str) -> str:
        """Generates a natural transition phrase between two news topics."""
        prompt = create_transition_phrase_prompt(previous_topic, current_topic, self.persona)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{CONFIG['ollama_api']['base_url']}/api/generate",
                    json={
                        'model': CONFIG["models"]["broadcast_model"],
                        'prompt': prompt,
                        'stream': False,
                        'options': {'temperature': 0.6, 'max_tokens': 50}
                    },
                    timeout=aiohttp.ClientTimeout(total=CONFIG["ollama_api"]["timeouts"]["transition"])
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data['response'].strip()
        except Exception as e:
            self.logger.error(f"Failed to generate transition phrase: {e}")
            return "Next, in the news."

    def clean_script_for_tts(self, script: str) -> str:
        """Clean script for better TTS playback"""
        script = re.sub(r'\[.*?\]', '', script)
        script = re.sub(r'\s+', ' ', script).strip()
        script = script.replace('...', '...')
        return script

    def save_results(self, script: str, segments: List[BroadcastSegment], filename: str):
        """Save the generated script and segment details to a Markdown file."""
        output_dir = Path("broadcast_logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# News Broadcast Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Full Broadcast Script\n")
            f.write(script)
            f.write("\n\n---\n\n")
            f.write("## Broadcast Segments Details\n")
            for i, segment in enumerate(segments):
                f.write(f"### Segment {i+1}: {segment.topic}\n")
                f.write(f"**Importance Score:** {segment.importance:.2f}\n")
                f.write("**Articles Included:**\n")
                for article in segment.articles:
                    f.write(f"- [{article.title}]({article.url})\n")
                    f.write(f"  - Summary: {article.summary}\n")
                    f.write(f"  - Sentiment: {article.sentiment_score:.2f}, Importance: {article.importance_score:.2f}, Relevancy: {article.relevancy_score:.2f}\n")
                f.write("\n")

        self.logger.info(f"Broadcast log saved to {filepath}")

    async def run_continuous(self, fetch_interval_minutes: int = 15):
        """
        Main continuous loop to fetch, process, and generate news audio.
        """
        self.logger.info("Starting continuous news generation stream.")

        previous_topic = None

        while True:
            try:
                self.logger.info("Fetching new batch of articles...")
                articles = await self.feed_fetcher.fetch_feeds_batch()
                self.performance_monitor.metrics['articles_processed'] += len(articles)

                if not articles:
                    self.logger.warning(f"No new articles found. Waiting for {fetch_interval_minutes} minutes.")
                    await asyncio.sleep(fetch_interval_minutes * 60)
                    continue

                processed_articles = await self.process_articles_smart(articles)
                segments = self.create_broadcast_segments(processed_articles)

                if not segments:
                    self.logger.info("No newsworthy segments created from the latest articles.")
                else:
                    self.logger.info(f"Generated {len(segments)} new broadcast segments.")

                    for i, segment in enumerate(segments):
                        self.logger.info(f"Processing segment {i+1}/{len(segments)}: {segment.topic}")

                        if i == 0:
                            intro_phrase = f"Welcome to your live news briefing. First up, {segment.topic}."
                        else:
                            transition_phrase = await self.generate_transition_phrase(previous_topic, segment.topic)
                            intro_phrase = f"{transition_phrase} Now, {segment.topic}."

                        segment_script = await self.generate_segment_script(segment)
                        full_script = self.clean_script_for_tts(f"{intro_phrase} {segment_script}")

                        await self.generate_and_queue_audio(full_script)

                        self.save_results(full_script, [segment], f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

                        previous_topic = segment.topic

                self.logger.info(f"Finished processing current batch. Waiting for {fetch_interval_minutes} minutes before next fetch.")
                await asyncio.sleep(fetch_interval_minutes * 60)

            except Exception as e:
                self.logger.error(f"An error occurred in the main loop: {e}", exc_info=True)
                self.logger.info("Restarting loop after a 5-minute cooldown.")
                await asyncio.sleep(300)
