"""
db/chroma.py — ChromaDB Vector Store (Feature 2)
HuggingFace sentence-transformers embeddings + persistent ChromaDB.
Collection: "newsspark_articles"
"""

import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "newsspark_articles"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_chroma_client = None
_collection = None
_embeddings = None


def _get_embeddings():
    """Lazy-load HuggingFace embeddings."""
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        print(f"[ChromaDB] Loading embedding model: {EMBEDDING_MODEL}")
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def init_chroma():
    """Initialize ChromaDB client and collection (synchronous — call at startup)."""
    global _chroma_client, _collection
    try:
        import chromadb
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"[ChromaDB] Initialized. Collection '{COLLECTION_NAME}' has {_collection.count()} docs.")
    except Exception as e:
        print(f"[ChromaDB] Init error: {e}")


def get_collection():
    global _collection
    if _collection is None:
        init_chroma()
    return _collection


def ingest_article(doc: dict):
    """
    Embed and store an article in ChromaDB.
    doc must have: title, content (or description), url, category, sentiment,
                   source_name (or source), published_at, _id (MongoDB ObjectId)
    """
    try:
        collection = get_collection()
        if collection is None:
            return

        title = doc.get("title", "")
        content = doc.get("content") or doc.get("description") or doc.get("raw_text") or ""
        url = doc.get("url", "")

        if not title or not url:
            return

        # Text to embed: title + first 500 chars of content
        text_to_embed = f"{title}. {content[:500]}"

        # Unique doc_id: use MongoDB _id if available, else hash URL
        import hashlib
        doc_id = str(doc.get("_id") or hashlib.md5(url.encode()).hexdigest())

        # Check if already exists
        existing = collection.get(ids=[doc_id])
        if existing and existing.get("ids"):
            return  # Already ingested

        embeddings = _get_embeddings()
        vector = embeddings.embed_query(text_to_embed)

        metadata = {
            "title": title[:200],
            "category": str(doc.get("category", "other")),
            "sentiment": str(doc.get("sentiment", "neutral")),
            "source": str(doc.get("source_name") or doc.get("source", "Unknown")),
            "published_at": str(doc.get("published_at", "")),
            "url": url[:500],
            "article_id": doc_id,
        }

        collection.add(
            ids=[doc_id],
            embeddings=[vector],
            documents=[text_to_embed],
            metadatas=[metadata],
        )
    except Exception as e:
        print(f"[ChromaDB] Ingest error for '{doc.get('title', '')[:50]}': {e}")


def get_retriever(
    categories: list | None = None,
    sentiment: str | None = None,
    k: int = 10,
):
    """
    Return a LangChain retriever backed by ChromaDB using MMR search.
    Supports optional metadata filtering by category / sentiment.
    """
    try:
        from langchain_chroma import Chroma
        from langchain_core.documents import Document

        embeddings = _get_embeddings()

        vectorstore = Chroma(
            client=_chroma_client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )

        # Build filter
        where_filter = None
        if categories and len(categories) == 1:
            where_filter = {"category": {"$eq": categories[0]}}
        elif categories and len(categories) > 1:
            where_filter = {"category": {"$in": categories}}
        if sentiment and where_filter:
            where_filter = {"$and": [where_filter, {"sentiment": {"$eq": sentiment}}]}
        elif sentiment:
            where_filter = {"sentiment": {"$eq": sentiment}}

        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,
                "fetch_k": k * 3,
                **({"filter": where_filter} if where_filter else {}),
            },
        )
        return retriever
    except Exception as e:
        print(f"[ChromaDB] Retriever error: {e}")
        return None


def similarity_search(query: str, k: int = 10, categories: list | None = None) -> list:
    """
    Direct similarity search returning list of dicts with article metadata.
    """
    try:
        from langchain_chroma import Chroma

        embeddings = _get_embeddings()
        vectorstore = Chroma(
            client=_chroma_client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )

        where_filter = None
        if categories and len(categories) == 1:
            where_filter = {"category": {"$eq": categories[0]}}
        elif categories and len(categories) > 1:
            where_filter = {"category": {"$in": categories}}

        docs = vectorstore.max_marginal_relevance_search(
            query,
            k=k,
            fetch_k=k * 3,
            filter=where_filter,
        )
        return [{"content": d.page_content, **d.metadata} for d in docs]
    except Exception as e:
        print(f"[ChromaDB] Search error: {e}")
        return []
