# How to Run NewsSpark Locally

NewsSpark is built with a separate **FastAPI Python Backend** and a **React + Vite Frontend**. You will need to start both servers in order to run the full application.

## Prerequisites
Ensure the following are installed on your system:
- **Python 3.9+**
- **Node.js (v18+) & NPM**
- **MongoDB Atlas Account** (for persistent data storage)
- **Groq API Key** (for Llama model inferencing)

---

## 🏗️ 1. Set Up the Backend (Python FastAPI)

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd newsspark
   ```

2. *(Optional but highly recommended)* Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install all required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your Environment Variables:
   - Create a `.env` file inside the `newsspark` folder.
   - Add your essential API keys:
     ```env
     # Required Keys
     GROQ_API_KEY=your_groq_key_here
     MONGO_URI=mongodb+srv://username:password@your-cluster.mongodb.net/NewsSpark

     # Optional / Free-Tier Fetcher Keys
     NEWSDATA_API_KEY=your_newsdata_io_key
     NEWSAPI_KEY=your_newsapi_org_key
     ```

5. Start the backend server:
   ```bash
   python main.py
   ```
   *The FastAPI server will boot up via Uvicorn (usually on port `8000`) and the APScheduler fetcher will immediately begin its background process.*

---

## 🎨 2. Set Up the Frontend (React Vite)

Keep the backend terminal running. Open a **new, split terminal window**.

1. Navigate to the frontend directory:
   ```bash
   cd newsspark-ui
   ```

2. Install all required Node packages:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *Vite natively routes `/api` and `/ws` backend requests securely via its local proxy (as configured in `vite.config.ts`), so no separate CORS or frontend `.env` configuration is needed.*

---

## 🚀 3. Start the Experience

Open your web browser and navigate to:
**[http://localhost:5173/](http://localhost:5173/)**

- The page will automatically render the News Feed.
- If the backend is running properly, the **WebSockets** will connect natively, and your feed will dynamically populate as the fetcher gathers news objects asynchronously!

### Troubleshooting & Logs
- **Database Checking**: If your feed looks empty after 2 minutes, open a third terminal and run `python debug_db.py` inside the `newsspark` folder. This script will tell you exactly how many unique articles and Story Arcs have been indexed.
- **Port Conflicts**: Ensure nothing else on your machine is using `8000` (Backend) or `5173` (Frontend).
