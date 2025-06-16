import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import logging

class SentimentAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analyzer = None
        self.setup_nltk()

    def setup_nltk(self):
        try:
            nltk.download('vader_lexicon', quiet=True)
            self.analyzer = SentimentIntensityAnalyzer()
        except Exception as e:
            self.logger.warning(f"NLTK setup failed: {e}")
            self.analyzer = None

    def get_sentiment_score(self, text: str) -> float:
        if self.analyzer:
            return self.analyzer.polarity_scores(text)['compound']
        return 0.0
