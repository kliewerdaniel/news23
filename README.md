# Automated News Broadcast Generator

This project creates an automated, continuous news broadcast stream by fetching articles from RSS feeds, processing them with advanced NLP techniques, and generating a dynamic news script with customizable personas. The script is converted to speech and played through a web interface, offering a personalized audio news experience.

## Features

* **Persona System:**
    * **Quantified Writing Style:** Uses numerical values (0.0-1.0) to precisely control:
        * Tone & Emotional Expression (warmth, enthusiasm, optimism, confidence)
        * Formality & Style (linguistic formality, vocabulary complexity)
        * Analytical Approach (systematic rigor, evidence dependency)
        * Perspective & Bias (objectivity, ideological neutrality)
        * Audience Engagement (accessibility, knowledge assumptions)
        * Rhetorical Devices (metaphor usage, narrative elements)
        * Citation & Authority (citation density, authority deference)
        * Uncertainty & Probability (epistemic stance, probabilistic reasoning)
        * Structural Preferences (organization style, transition explicitness)
    * **Dynamic Prompt Generation:** Automatically maps persona traits to natural language intensities
    * **Multiple Personas:** Includes pre-configured personas like objective, satirist, and quantitative

* **Web Interface:** Access and control the news broadcast through a FastAPI-powered web interface
* **Continuous News Stream:** Automatically fetches and processes news at a defined interval
* **Intelligent Article Processing:**
    * **Feed Fetching:** Asynchronously gathers articles from multiple RSS feeds
    * **Content Extraction:** Cleans HTML content and skips duplicate articles using content hashing
    * **Summarization:** Uses Ollama for local LLM-powered article summarization
    * **Relevancy Scoring:** Scores articles based on their relevance to user-defined topics
    * **Stream Clustering:** Groups similar articles using advanced streaming clustering algorithms
    * **Sentiment Analysis:** Analyzes emotional tone using TextBlob
    * **Importance Scoring:** Ranks articles based on freshness, content quality, readability, and sentiment
* **Dynamic Script Generation:**
    * **Persona System:** Uses YAML-defined personas to customize news delivery style
    * **Smart Transitions:** Generates natural transitions between news segments
    * **Context-Aware:** Incorporates multiple related articles into coherent segments
* **Robust Audio System:**
    * **Queue-based Playback:** Streams audio seamlessly using a threaded queue system
    * **Edge TTS Integration:** Converts scripts to natural-sounding speech
* **System Reliability:**
    * **Circuit Breaker:** Prevents system overload during API calls
    * **Performance Monitoring:** Tracks metrics like processing times and success rates
    * **Persistent Storage:** Caches processed articles in SQLite
    * **Comprehensive Logging:** Detailed operation logs and broadcast archives

## Prerequisites

* **Python 3.8+**
* **Ollama:**
    * Install from [ollama.com](https://ollama.com/)
    * Required models:
        ```bash
        ollama run mistral-small:24b-instruct-2501-q8_0
        ```
* **Spacy Language Model:**
    ```bash
    python -m spacy download en_core_web_sm
    ```

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/kliewerdaniel/news23.git
    cd news23
    ```

2. Create and activate virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. **feeds.yaml:** Create this in the root directory to specify RSS feeds:
    ```yaml
    feeds:
      - https://www.reuters.com/arc/feed/rss/
      - https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml
      - https://feeds.bbci.co.uk/news/rss.xml
    ```

2. **personas:** Customize news delivery style in the personas directory:
    ```yaml
    # personas/objective.yaml example
    style: "formal and factual"
    tone: "neutral"
    instructions: "Present news in a clear, unbiased manner..."
    ```

## Persona System Details

### Quantized Style Values (0.0 = minimum, 1.0 = maximum)

The persona system uses precise numerical values to control various aspects of writing style. Example from quant.yaml:

```yaml
# TONE AND EMOTIONAL EXPRESSION
emotional_warmth: 0.3              # 0.0 = cold/detached, 1.0 = warm/empathetic
enthusiasm_level: 0.2              # 0.0 = dispassionate, 1.0 = highly enthusiastic
optimism_bias: 0.5                 # 0.0 = pessimistic, 1.0 = optimistic

# FORMALITY AND STYLE
linguistic_formality: 0.9          # 0.0 = casual/colloquial, 1.0 = highly formal
vocabulary_complexity: 0.8         # 0.0 = simple/accessible, 1.0 = advanced/technical

# More categories include: Analytical Approach, Perspective & Bias, Audience Engagement,
# Rhetorical Devices, Citation & Authority, Uncertainty & Probability, and Structural Preferences
```

### Prompt Generation

The system uses three main prompt types, each incorporating the persona's quantized traits:

1. **Article Summary Prompt:**
```
You are writing as a [name].

Description: [description]

# TONE AND EMOTIONAL EXPRESSION
Emotional Warmth: [mapped intensity (e.g., "very cold/detached")]
Enthusiasm Level: [mapped intensity]
[... other traits mapped to intensities ...]

Please summarize the following article accordingly in 6 sentences:
[article_title]
[article_content]
```

2. **News Segment Script Prompt:**
```
You are writing as a [name].

Description: [description]
[... personality profile with mapped intensities ...]

Write a news segment about [topic]. Use this information:
[context]

Write 7-10 sentences in a concise style, focusing directly on the news.
[optional guidance]
```

3. **Transition Phrase Prompt:**
```
You are a news anchor with the following persona:

Description: [description]
[... personality profile with mapped intensities ...]

Generate a short, smooth transition phrase (1-2 sentences) from a news segment 
about '[previous_topic]' to a new segment about '[current_topic]'.
```

## Usage

1. **Start the Web Server:**
    ```bash
    python main.py
    ```

2. **Access the Interface:**
   Open http://localhost:8000 in your browser

3. **Control Options:**
   * Start/stop the news broadcast
   * Select news personas
   * Set topic filters
   * Adjust fetch intervals
   * Provide custom guidance

## Project Structure

```
.
├── main.py                   # FastAPI web server and main entry point
├── feeds.yaml               # RSS feed configuration
├── personas/               # News delivery style definitions
│   ├── objective.yaml
│   ├── satirist.yaml
│   └── ...
├── src/
│   ├── audio/             # Audio generation and playback
│   ├── core/             # Core processing logic
│   ├── data/             # Database and data management
│   ├── feeds/            # Feed fetching and processing
│   └── nlp/              # NLP utilities and clustering
├── broadcast_logs/        # Generated broadcast archives
└── news.log              # Application logging
```

## Dependencies

Core dependencies include:
* `fastapi` & `uvicorn`: Web interface and API
* `aiohttp`: Async HTTP operations
* `edge-tts`: Text-to-speech generation
* `ollama`: Local LLM integration
* `spacy`: NLP processing
* `textblob`: Sentiment analysis
* `scikit-learn`: ML utilities
* `gradio`: UI components
* `sentence-transformers`: Text embeddings
* Additional utilities: `pyyaml`, `newspaper3k`, `geopy`

## Troubleshooting

* **Web Interface Issues:**
    * Verify the server is running at http://localhost:8000
    * Check news.log for error messages
    * Ensure all static files are present

* **Audio Problems:**
    * Confirm edge-tts installation
    * Verify system audio configuration
    * Check audio queue status in logs

* **Processing Issues:**
    * Ensure Ollama server is running
    * Verify model availability
    * Check circuit breaker status
    * Monitor performance metrics

* **Feed Issues:**
    * Validate feeds.yaml format
    * Check feed URLs are accessible
    * Review feed fetcher logs

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.
