import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime
import aiohttp # Import aiohttp
from sklearn.metrics import silhouette_score
import time # Import time for sleep
import traceback # Import traceback
from src.core.config import CONFIG # Import CONFIG
from src.core.circuit_breaker import CircuitBreaker # Import CircuitBreaker
from src.prompts import create_summary_prompt, create_segment_script_prompt, create_transition_phrase_prompt # Import prompt functions

class CSAIHistory:
    def __init__(self):
        self.history = []

    def append(self, data):
        self.history.append(data)

class StreamClusterer:
    def __init__(self, embedding_model='sentence-transformers/all-MiniLM-L6-v2', n_clusters=5):
        self.embedder = SentenceTransformer(embedding_model)
        self.kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=0, batch_size=256, n_init='auto') # Increased n_init for more stable results
        self.csai_history = CSAIHistory()
        self.cluster_history = [] # Store cluster summaries and metadata
        self.geolocator = Nominatim(user_agent="news15", timeout=10) # Increased timeout
        self.session: aiohttp.ClientSession = None # Will be set by NewsGenerator
        self.circuit_breaker: CircuitBreaker = None # Will be set by NewsGenerator

    def add_batch(self, headlines):
        if not headlines:
            return {} # Return empty if no headlines

        embeddings = self.embedder.encode(headlines, convert_to_tensor=True)
        embeddings_np = embeddings.cpu().numpy()

        # Handle cases where n_clusters might be greater than n_samples
        if len(headlines) < self.kmeans.n_clusters:
            # Assign all to a single cluster if not enough samples for multiple clusters
            cluster_labels = np.zeros(len(headlines), dtype=int)
        else:
            # Fit incrementally and then predict
            self.kmeans.partial_fit(embeddings_np)
            cluster_labels = self.kmeans.predict(embeddings_np)

        clustered_headlines = {}
        for i, label in enumerate(cluster_labels):
            if label not in clustered_headlines:
                clustered_headlines[label] = []
            clustered_headlines[label].append(headlines[i])
        return clustered_headlines

    async def postprocess_cluster(self, cluster_headlines, timestamp_source_info=None):
        filtered_headlines = self.temporal_spatial_filter(cluster_headlines, timestamp_source_info)
        cluster_summary = await self.summarize_cluster(filtered_headlines)
        cluster_topic = await self.label_cluster_topic(cluster_summary)

        return {
            'summary': cluster_summary,
            'topic': cluster_topic,
            'headlines': filtered_headlines
        }

    def temporal_spatial_filter(self, headlines, timestamp_source_info):
        filtered_headlines = []
        if not CONFIG["processing"]["enable_spatial_filter"]:
            # If spatial filter is disabled, only apply temporal filter
            if timestamp_source_info:
                for i, headline in enumerate(headlines):
                    timestamp, _ = timestamp_source_info[i]
                    if (datetime.now() - timestamp).total_seconds() <= 24 * 3600:
                        filtered_headlines.append(headline)
            else:
                filtered_headlines = headlines
            return filtered_headlines

        # Proceed with spatial filtering if enabled
        if timestamp_source_info:
            austin_coords = None
            try:
                austin_location = self.geolocator.geocode("Austin, Texas")
                if austin_location:
                    austin_coords = (austin_location.latitude, austin_location.longitude)
                else:
                    print("Warning: Could not geocode 'Austin, Texas'. Skipping spatial filter.")
            except Exception as e:
                print(f"Error geocoding 'Austin, Texas': {e}. Skipping spatial filter.")

            if austin_coords:
                for i, headline in enumerate(headlines):
                    timestamp, source = timestamp_source_info[i]
                    try:
                        source_location = self.geolocator.geocode(source)
                        if source_location:
                            source_coords = (source_location.latitude, source_location.longitude)
                            distance = geodesic(austin_coords, source_coords).miles
                            # Basic temporal filter: keep headlines from the last 24 hours
                            if (datetime.now() - timestamp).total_seconds() <= 24 * 3600 and distance <= 100:
                                filtered_headlines.append(headline)
                        else:
                            print(f"Warning: Could not geocode source '{source}'. Skipping headline: {headline}")
                    except Exception as e:
                        print(f"Error geocoding source '{source}': {e}. Skipping headline: {headline}")
                    time.sleep(1) # Add a delay to respect API rate limits
            else:
                # If Austin couldn't be geocoded, skip spatial filtering and just apply temporal
                for i, headline in enumerate(headlines):
                    timestamp, _ = timestamp_source_info[i]
                    if (datetime.now() - timestamp).total_seconds() <= 24 * 3600:
                        filtered_headlines.append(headline)
        else:
            filtered_headlines = headlines
        return filtered_headlines

    async def summarize_cluster(self, headlines):
        if not headlines:
            return "No headlines to summarize"
        text = " ".join(headlines)

        if not self.session or not self.circuit_breaker.can_execute():
            return "Summary unavailable (LLM service not configured or circuit breaker open)."

        prompt = create_summary_prompt("Cluster Summary", text, {}) # No persona for cluster summary

        try:
            async with self.session.post(
                f"{CONFIG['ollama_api']['base_url']}/api/generate",
                json={
                    'model': CONFIG["models"]["summary_model"],
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.3, 'max_tokens': 500}
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self.circuit_breaker.record_success()
                return data['response'].strip()
        except aiohttp.ClientResponseError as e:
            error_detail = await e.response.text() if e.response else "No response body"
            print(f"ERROR - Cluster summary LLM API error (status: {e.status}): {error_detail}")
            self.circuit_breaker.record_failure()
            return "Summary unavailable due to LLM error."
        except aiohttp.ClientError as e:
            print(f"ERROR - Network error during cluster summary LLM call: {e}")
            self.circuit_breaker.record_failure()
            return "Summary unavailable due to LLM error."
        except Exception as e:
            print(f"ERROR - Unexpected error during cluster summary LLM call: {e}")
            traceback.print_exc() # Print the full traceback
            self.circuit_breaker.record_failure()
            return "Summary unavailable due to LLM error."

    async def label_cluster_topic(self, cluster_summary):
        if not cluster_summary or not self.session or not self.circuit_breaker.can_execute():
            return "Topic unavailable (LLM service not configured or circuit breaker open)."

        prompt = f"What is the main topic of the following text? {cluster_summary}\n\nTopic:"
        
        try:
            async with self.session.post(
                f"{CONFIG['ollama_api']['base_url']}/api/generate",
                json={
                    'model': CONFIG["models"]["broadcast_model"], # Using broadcast model for topic extraction
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.6, 'max_tokens': 50}
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self.circuit_breaker.record_success()
                return data['response'].strip()
        except aiohttp.ClientResponseError as e:
            error_detail = await e.response.text() if e.response else "No response body"
            print(f"ERROR - Topic extraction LLM API error (status: {e.status}): {error_detail}")
            self.circuit_breaker.record_failure()
            return "Topic unavailable due to LLM error."
        except aiohttp.ClientError as e:
            print(f"ERROR - Network error during topic extraction LLM call: {e}")
            self.circuit_breaker.record_failure()
            return "Topic unavailable due to LLM error."
        except Exception as e:
            print(f"ERROR - Unexpected error during topic LLM call: {e}")
            self.circuit_breaker.record_failure()
            return "Topic unavailable due to LLM error."

    def validate_clustering(self, embeddings, labels):
        # Only calculate silhouette score if there are at least two unique labels
        # and more than one sample, otherwise it's undefined.
        if len(np.unique(labels)) > 1 and len(embeddings) > 1:
            silhouette = silhouette_score(embeddings, labels)
            self.csai_history.append({'silhouette': silhouette})
            return silhouette
        else:
            # If silhouette score cannot be calculated, append a placeholder or skip
            self.csai_history.append({'silhouette': None})
            return None

    async def process_batch(self, headlines, timestamp_source_info=None):
        clustered_headlines = self.add_batch(headlines)
        cluster_results = {}
        embeddings = self.embedder.encode(headlines, convert_to_tensor=True).cpu().numpy()
        # Ensure labels are available, especially if clustering was skipped
        if len(headlines) < self.kmeans.n_clusters:
            labels = np.zeros(len(headlines), dtype=int)
        else:
            labels = self.kmeans.labels_

        for cluster_id, cluster_headlines_list in clustered_headlines.items():
            # Filter timestamp_source_info for the current cluster's headlines
            current_cluster_ts_info = []
            for hl in cluster_headlines_list:
                try:
                    idx = headlines.index(hl)
                    current_cluster_ts_info.append(timestamp_source_info[idx])
                except ValueError:
                    # This should not happen if headlines are correctly matched
                    pass
            cluster_results[cluster_id] = await self.postprocess_cluster(cluster_headlines_list, current_cluster_ts_info)

        self.validate_clustering(embeddings, labels)
        self.cluster_history.append(cluster_results)
        return cluster_results

    def get_cluster_history(self):
        return self.cluster_history
