"""
RAG Retriever.

Provides semantic search over ingested financial documents with
metadata filtering and relevance scoring.

Usage::

    from src.rag.retriever import RAGRetriever
    retriever = RAGRetriever()

    # Search filings
    results = retriever.search("revenue growth drivers", symbol="AAPL")

    # Search with filing type filter
    results = retriever.search(
        "risk factors",
        symbol="AAPL",
        filing_type="10-K",
        top_k=10,
    )

    # Get context string for LLM
    context = retriever.get_context_for_llm(
        "What are AAPL's main risk factors?",
        symbol="AAPL",
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.rag.embedder import Embedder
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RAGRetriever:
    """
    Retrieves relevant document chunks from the RAG vector store.

    Wraps ``Embedder.query()`` with convenience methods for common
    financial document retrieval patterns.
    """

    def __init__(self, embedder: Optional[Embedder] = None) -> None:
        self._embedder = embedder or Embedder()

    # ── Core search ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        symbol: Optional[str] = None,
        filing_type: Optional[str] = None,
        doc_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks.

        Args:
            query: Natural language search query.
            symbol: Filter by stock ticker.
            filing_type: Filter by SEC filing type (10-K, 10-Q, 8-K).
            doc_type: Filter by document type (filing, transcript).
            top_k: Number of results to return.

        Returns:
            List of dicts with 'text', 'metadata', 'relevance_score'.
        """
        where = {}
        if symbol:
            where["symbol"] = symbol.upper()
        if filing_type:
            where["filing_type"] = filing_type
        if doc_type:
            where["doc_type"] = doc_type

        results = self._embedder.query(
            query_text=query,
            n_results=top_k,
            where=where if where else None,
        )

        # Convert to list of result dicts with relevance scores
        output = []
        for text, meta, dist, doc_id in zip(
            results["documents"],
            results["metadatas"],
            results["distances"],
            results["ids"],
        ):
            # ChromaDB distance is L2; convert to similarity score (0-1)
            relevance = max(0, 1.0 - (dist / 2.0))
            output.append({
                "text": text,
                "metadata": meta,
                "relevance_score": round(relevance, 3),
                "id": doc_id,
            })

        return output

    # ── Convenience methods ──────────────────────────────────────

    def search_filings(
        self,
        query: str,
        symbol: str,
        filing_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search SEC filings for a specific company."""
        return self.search(
            query=query,
            symbol=symbol,
            filing_type=filing_type,
            doc_type=None,
            top_k=top_k,
        )

    def search_transcripts(
        self,
        query: str,
        symbol: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search earnings call transcripts for a specific company."""
        return self.search(
            query=query,
            symbol=symbol,
            doc_type="transcript",
            top_k=top_k,
        )

    def get_context_for_llm(
        self,
        query: str,
        symbol: Optional[str] = None,
        filing_type: Optional[str] = None,
        top_k: int = 5,
        max_context_chars: int = 8000,
    ) -> str:
        """
        Retrieve relevant chunks and format them as a context string
        suitable for injecting into an LLM prompt.

        Args:
            query: The question/analysis query.
            symbol: Filter by ticker.
            filing_type: Filter by filing type.
            top_k: Number of chunks to retrieve.
            max_context_chars: Max total context length.

        Returns:
            Formatted context string with source citations.
        """
        results = self.search(
            query=query,
            symbol=symbol,
            filing_type=filing_type,
            top_k=top_k,
        )

        if not results:
            return "No relevant documents found in the knowledge base."

        sections = []
        total_chars = 0

        for i, r in enumerate(results, start=1):
            meta = r["metadata"]
            source = (
                f"{meta.get('symbol', '?')} "
                f"{meta.get('filing_type', meta.get('doc_type', '?'))} "
                f"(filed {meta.get('filed_date', 'unknown')})"
            )
            header = f"[Source {i}: {source} | Relevance: {r['relevance_score']:.0%}]"
            text = r["text"]

            # Respect context budget
            if total_chars + len(text) > max_context_chars:
                remaining = max_context_chars - total_chars
                if remaining > 200:
                    text = text[:remaining] + "..."
                else:
                    break

            sections.append(f"{header}\n{text}")
            total_chars += len(text) + len(header)

        return "\n\n---\n\n".join(sections)

    # ── Stats ────────────────────────────────────────────────────

    def document_count(self, symbol: Optional[str] = None) -> int:
        """Return the number of documents, optionally filtered by symbol."""
        if symbol:
            results = self._embedder.query(
                query_text="",
                n_results=1,
                where={"symbol": symbol.upper()},
            )
            # Approximate — ChromaDB doesn't expose filtered count easily
            return len(results.get("documents", []))
        return self._embedder.count()

    def has_documents(self, symbol: str) -> bool:
        """Check if any documents exist for a symbol."""
        return self.document_count(symbol) > 0
