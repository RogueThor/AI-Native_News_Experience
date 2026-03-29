<div align="center">
  <h1>🗞️ NewsSpark</h1>
  <p><strong>The AI-Native News Experience</strong></p>
  <p><i>Curated, Deduplicated, and Interactive Vernacular News without the Noise.</i></p>
</div>

---

## 📖 Overview

**NewsSpark** is an intelligent, real-time news platform engineered to cut through the information overload of modern journalism. 

By leveraging asynchronous Python agents, vector search, and Large Language Models (LLMs), NewsSpark fetches headlines concurrently across multiple publishers, strictly groups identical news events to eliminate repetition, and visualizes them natively into chronological **Story Arcs**.

Users experience news through a stunning, glassmorphic React interface loaded with immersive features like an **AI Reporter** (Text-to-Speech), **Executive Dossiers**, and fluent **Vernacular Translations**.

---

## 🌟 Key Features
- **Smart Deduplication**: AI groups identical headlines from different publishers into a single, unified story event.
- **Dynamic Story Arcs**: Chronological, multi-article timelines for deep-dive reading on trending topics.
- **AI Reporter (TTS)**: A live Web Speech API broadcast of article summaries, guided by an interactive digital anchor.
- **Catch Me Up**: Conversational logic routing that lets users chat with an AI specifically contextualized on breaking news.
- **Executive Briefings**: Analytical dossiers on key sectors (Markets, Startups, RBI) equipped with a dedicated Q&A module.
- **Vernacular Translation**: High-accuracy translations into Regional Languages (Hindi, Tamil) leveraging 70B parameter models.

---

## 📚 Ecosystem Documentation

For an exhaustive breakdown of how NewsSpark is built, what models are used, and how to spin it up natively, please review the dedicated documentation below:

1. [**Architecture & Features Overview**](Architecture_and_Features.md)  
   *A full breakdown of the Tech Stack, APIs, Backend Agents, and a system Architecture map.*

2. [**Local Setup & Run Instructions**](How_To_Run.md)  
   *Step-by-step commands to install dependencies, configure API keys, and run the Python FastAPI background fetcher alongside the Vite React Frontend.*

---

## 🛠️ Stack Summary

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | React 18, Vite, TypeScript, Pure CSS (Glassmorphism), Web Speech API |
| **Backend** | Python 3, FastAPI, Uvicorn, APScheduler |
| **AI Models** | Groq (`llama-3.1-8b` / `llama-3.3-70b`) |
| **Data Storage** | MongoDB Atlas, ChromaDB, SQLite |
| **News Sources** | pygooglenews, NewsData.io, NewsAPI, RSS (feedparser) |
