"""
RAG (Retrieval-Augmented Generation) Pipeline.

Provides document ingestion, embedding, and retrieval for SEC filings
and earnings transcripts, enabling agents to reason over real financial
documents.

Architecture::

    SEC EDGAR / Transcripts
          │
    ┌─────▼──────┐
    │  Ingester   │  ← fetch, chunk, tag metadata
    └─────┬──────┘
          │
    ┌─────▼──────┐
    │  Embedder   │  ← embed chunks via Sentence Transformers
    └─────┬──────┘
          │
    ┌─────▼──────┐
    │  ChromaDB   │  ← persist embeddings with metadata
    └─────┬──────┘
          │
    ┌─────▼──────┐
    │  Retriever  │  ← similarity search + metadata filters
    └────────────┘
"""

from src.rag.ingester import SECIngester
from src.rag.retriever import RAGRetriever

__all__ = ["RAGRetriever", "SECIngester"]
