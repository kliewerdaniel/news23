CONFIG = {
    "ollama_api": {
        "base_url": "http://localhost:11434",
        "timeouts": {
            "summary": 120,  # 2 minutes for summary generation
            "relevancy": 60,  # 1 minute for relevancy scoring
            "segment": 120,   # 2 minutes for segment script generation
            "transition": 60  # 1 minute for transition phrases
        }
    },
    "models": {
        "summary_model": "mistral-small:24b-instruct-2501-q8_0",
        "broadcast_model": "mistral-small:24b-instruct-2501-q8_0",
        "embedding_model": "nomic-embed-text"
    },
    "processing": {
        "max_articles_per_feed": 20,
        "min_article_length": 50,
        "max_clusters": 50,
        "target_segments": 50000,
        "enable_spatial_filter": False # New configuration option
    },
    "relevancy": {
        "threshold": 3 # Lowered default relevancy threshold
    },
    "output": {"max_broadcast_length": 900000000}
}
