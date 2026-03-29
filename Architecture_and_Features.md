# NewsSpark - Architecture & Features Overview


## 1. Core Features Implemented

1. **Multi-Source Asynchronous News Fetcher**
   - Fetches news concurrently from 5+ distinct source types (RSS, Google News, custom APIs) using `asyncio` to eliminate blocking.
   - Cleans HTML content, extracts primary images, and deduplicates identical articles via MD5 URL hashing.

2. **AI-Powered Deduplication & Classification**
   - A highly optimized batch classifier bundles articles into groups of 10 and sends them to the LLM.
   - The AI natively categorizes the article (Business, Technology, Sports, etc.), assigns a sentiment score (Positive, Negative, Neutral), and generates a `story_slug`.

3. **Dynamic Story Arc Clustering**
   - Implements strict Title-based Fuzzy Matching to fuse identical news events across varying sources into deep, chronological timelines.
   - Uses a "Singleton Exterminator" rule so the UI only displays the `Story Arc` button when multiple related articles exist, preventing isolated, 1-article arcs.

4. **Real-Time WebSocket Feed**
   - Connected React clients are subscribed to live updates via FastAPIs WebSocket endpoints.
   - When the APScheduler completes a background fetch round, it securely pushes new articles to active UI clients without requiring a page refresh.

5. **AI Reporter (Text-to-Speech Animation)**
   - Transforms standard reading into an interactive broadcast.
   - Parses the summary of an article and uses the browser's native Web Speech API to read the news aloud. Syncs voice cadence with a custom AI Anchor GIF animation.

6. **Executive Briefings**
   - Produces high-level intelligence dossiers on specific sectors (e.g., Markets, RBI, Startups).
   - Generates an analytical readout of trending topics, complete with an interactive Q&A slide-out drawer where the AI answers questions based *only* on the generated briefing context.

7. **Vernacular Translation**
   - Seamless, on-demand translation of core Indian news into Hindi and Tamil utilizing the 70B parameter LLM, preserving nuance and regional context.

8. **Catch Me Up (Conversational AI)**
   - A dedicated chat interface leveraging LangGraph routing to answer user questions regarding recent global and regional events logically and contextually.

9. **Graceful Fallbacks & Glassmorphic UI**
   - Implements robust error handling. For instance, if an API fails to provide an article image, a deterministic MD5 hash of the title maps to a high-quality Unsplash placeholder.

---

## 2. AI Models Used

NewsSpark utilizes a centralized model configuration (`agents.model_config.py`) routed entirely through the **Groq Platform** to achieve lightning-fast inference times.

*   **`llama-3.1-8b-instant`**: 
    - *Purpose*: High-volume, high-throughput tasks.
    - *Usage*: Bulk news classification (categorization, sentiment analysis, story slug generation). This preserves the strict token quotas on the larger models while retaining excellent extraction accuracy.
*   **`llama-3.3-70b-versatile`**: 
    - *Purpose*: Deep reasoning, content generation, and vernacular nuance.
    - *Usage*: Generating Executive Briefings, synthesizing multi-article Story Arcs, accurately translating into Hindi and Tamil, and handling Catch-Me-Up conversational queries.

---

## 3. APIs & Third-Party Integrations

> **Note**: No API keys or secrets are documented below. All integrations use their standard public interfaces.

*   **Groq API**: Provider for ultra-fast Llama 3 model inference.
*   **NewsData.io API**: Primary data source for fetching structured Indian news.
*   **NewsAPI (newsapi.org)**: Fallback secondary fetcher engaged only when primary sources fail or return insufficient counts.
*   **Marketaux API**: Supplementary API providing global and regional market/stock news.
*   **Google News (`pygooglenews`)**: Unofficial Python wrapper mapping Google News RSS endpoints to structured Python data.
*   **RSS Feeds (`feedparser`)**: Direct syndication from Times of India, NDTV, Livemint, Economic Times, and BBC India.
*   **Unsplash**: Provides dynamic, high-resolution aesthetic fallbacks for articles missing primary images.
*   **Web Speech API**: In-browser native API used to synthesize and play the Text-to-Speech audio for the AI Reporter and Executive Briefings natively without backend latency.

---

## 4. Technology Stack

### Frontend
*   **Framework**: React 18 & Vite
*   **Language**: TypeScript / JSX
*   **Styling**: Pure CSS utilizing a modern Glassmorphism design system (blur filters, gradients, accessible contrast).
*   **Routing**: `react-router-dom`

### Backend
*   **Framework**: FastAPI (Python 3) & Uvicorn ASGI server
*   **Orchestration**: `APScheduler` for autonomous background fetching loops.
*   **AI Architecture**: Direct API endpoints configured with `langchain_core` prompt templates and `langgraph` concepts.

### Databases & Storage
*   **MongoDB Atlas**: The central source of truth for persistent data, storing users, unique articles, extracted concepts, and pre-compiled Story Arcs.
*   **ChromaDB**: Local vector database intended for high-speed semantic search similarity (Note: Explicitly disabled on Windows builds to prevent known native Rust panics).
*   **SQLite**: Used exclusively for local agent execution logging and local caching routines (`db.sqlite` / `newsspark_cache.db`).
