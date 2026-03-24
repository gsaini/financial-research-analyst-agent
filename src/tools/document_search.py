"""
Document Search Tool (RAG).

Provides LangChain ``@tool``-decorated functions that agents can use
to search ingested SEC filings and earnings transcripts.

Usage::

    from src.tools.document_search import search_filings, search_transcripts

    # As a LangChain tool (bound to an agent)
    result = search_filings("AAPL", "10-K", "revenue growth drivers")

    # Ingest documents first
    from src.tools.document_search import ingest_company_filings
    count = await ingest_company_filings("AAPL")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy-init singleton to avoid import-time ChromaDB initialization
_retriever = None
_ingester = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        from src.rag.retriever import RAGRetriever
        _retriever = RAGRetriever()
    return _retriever


def _get_ingester():
    global _ingester
    if _ingester is None:
        from src.rag.ingester import SECIngester
        _ingester = SECIngester()
    return _ingester


# ── LangChain Tools ─────────────────────────────────────────────


@tool("search_sec_filings")
def search_filings(
    symbol: str,
    filing_type: str,
    query: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Search SEC filings (10-K, 10-Q, 8-K) for a company using semantic search.

    This tool searches over previously ingested SEC filings and returns
    the most relevant text passages. Use this to find specific information
    in annual reports (10-K), quarterly reports (10-Q), or material
    event reports (8-K).

    Args:
        symbol: Stock ticker (e.g., "AAPL", "MSFT").
        filing_type: SEC filing type — "10-K", "10-Q", or "8-K".
        query: Natural language search query describing what you're looking for.
        top_k: Number of results to return (default 5).

    Returns:
        Dict with matching passages, their source metadata, and relevance scores.
    """
    retriever = _get_retriever()
    results = retriever.search_filings(
        query=query,
        symbol=symbol,
        filing_type=filing_type,
        top_k=top_k,
    )

    return {
        "symbol": symbol,
        "filing_type": filing_type,
        "query": query,
        "total_results": len(results),
        "results": [
            {
                "text": r["text"][:500],  # Truncate for tool output
                "relevance": r["relevance_score"],
                "filed_date": r["metadata"].get("filed_date", "unknown"),
            }
            for r in results
        ],
    }


@tool("search_earnings_transcripts")
def search_transcripts(
    symbol: str,
    query: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Search earnings call transcripts for a company using semantic search.

    Use this tool to find specific management commentary, guidance
    language, or analyst Q&A from earnings calls.

    Args:
        symbol: Stock ticker (e.g., "AAPL").
        query: What you're looking for in the transcripts.
        top_k: Number of results to return.

    Returns:
        Dict with matching transcript passages and relevance scores.
    """
    retriever = _get_retriever()
    results = retriever.search_transcripts(
        query=query,
        symbol=symbol,
        top_k=top_k,
    )

    return {
        "symbol": symbol,
        "query": query,
        "total_results": len(results),
        "results": [
            {
                "text": r["text"][:500],
                "relevance": r["relevance_score"],
                "metadata": {
                    k: v for k, v in r["metadata"].items()
                    if k in ("quarter", "year", "doc_type", "filed_date")
                },
            }
            for r in results
        ],
    }


@tool("get_filing_context")
def get_filing_context(
    symbol: str,
    query: str,
    filing_type: str = "",
    max_context_chars: int = 6000,
) -> str:
    """
    Retrieve relevant SEC filing passages as a formatted context block
    that can be used for deeper analysis.

    Unlike search_sec_filings which returns structured results, this tool
    returns a single formatted text block with source citations — ideal
    for feeding into analysis prompts.

    Args:
        symbol: Stock ticker.
        query: What you need context about.
        filing_type: Optional filter (10-K, 10-Q, 8-K).
        max_context_chars: Maximum context length.

    Returns:
        Formatted context string with source citations.
    """
    retriever = _get_retriever()
    return retriever.get_context_for_llm(
        query=query,
        symbol=symbol,
        filing_type=filing_type or None,
        max_context_chars=max_context_chars,
    )


# ── Ingestion (not a @tool — called programmatically) ───────────


async def ingest_company_filings(
    symbol: str,
    filing_types: Optional[List[str]] = None,
    max_filings: int = 3,
) -> Dict[str, Any]:
    """
    Ingest SEC filings for a company into the RAG vector store.

    Call this before using search tools to ensure documents are available.

    Args:
        symbol: Stock ticker.
        filing_types: Filing types to ingest. Default: ["10-K", "10-Q"].
        max_filings: Max filings per type to fetch.

    Returns:
        Dict with ingestion stats.
    """
    ingester = _get_ingester()
    count = await ingester.ingest_filings(
        symbol=symbol,
        filing_types=filing_types,
        max_filings=max_filings,
    )
    return {
        "symbol": symbol,
        "filing_types": filing_types or ["10-K", "10-Q"],
        "chunks_ingested": count,
        "status": "success" if count > 0 else "no_data",
    }


async def ingest_earnings_transcript(
    symbol: str,
    text: str,
    quarter: str = "",
    year: str = "",
) -> Dict[str, Any]:
    """
    Ingest an earnings call transcript into the RAG vector store.

    Args:
        symbol: Stock ticker.
        text: Full transcript text.
        quarter: e.g., "Q1", "Q2".
        year: e.g., "2024".

    Returns:
        Dict with ingestion stats.
    """
    ingester = _get_ingester()
    metadata = {}
    if quarter:
        metadata["quarter"] = quarter
    if year:
        metadata["year"] = year

    count = await ingester.ingest_text(
        text=text,
        symbol=symbol,
        doc_type="transcript",
        metadata=metadata,
    )
    return {
        "symbol": symbol,
        "doc_type": "transcript",
        "quarter": quarter,
        "year": year,
        "chunks_ingested": count,
        "status": "success" if count > 0 else "no_data",
    }
