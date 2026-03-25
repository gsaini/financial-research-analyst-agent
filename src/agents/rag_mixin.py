"""
RAG Mixin for Financial Research Agents.

Provides Retrieval-Augmented Generation capabilities that any agent
can opt into by inheriting from ``RAGMixin``.  The mixin handles
document ingestion, context retrieval, and task enrichment while
gracefully degrading when the RAG subsystem is unavailable.

Usage::

    class FundamentalAnalyst(RAGMixin, BaseAgent):
        ...

        async def analyze(self, symbol: str) -> AgentResult:
            await self.ensure_ingested(symbol)
            context = self.get_rag_context(symbol, ["revenue drivers", "risk factors"])
            ...
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Session-level cache of symbols that have already been ingested.
_ingested_symbols: Set[str] = set()


class RAGMixin:
    """Mixin that gives agents RAG (Retrieval-Augmented Generation) capabilities.

    Attributes:
        _rag_enabled: Whether RAG features are active.  Defaults to ``True``
            but automatically falls back to ``False`` if the underlying
            document-search tooling is unavailable.
    """

    _rag_enabled: bool = True

    # ------------------------------------------------------------------
    # Ingestion helpers
    # ------------------------------------------------------------------

    async def ensure_ingested(
        self,
        symbol: str,
        filing_types: Optional[List[str]] = None,
        max_filings: int = 3,
    ) -> bool:
        """Ensure SEC filings for *symbol* have been ingested this session.

        Skips ingestion if the symbol was already processed.  Returns
        ``True`` if documents are available, ``False`` otherwise.
        """
        if not self._rag_enabled:
            return False

        symbol = symbol.upper()
        cache_key = f"{symbol}|{'|'.join(sorted(filing_types or ['10-K', '10-Q']))}"

        if cache_key in _ingested_symbols:
            logger.debug("RAG documents for {} already ingested, skipping.", symbol)
            return True

        try:
            from src.tools.document_search import ingest_company_filings

            result = await ingest_company_filings(
                symbol=symbol,
                filing_types=filing_types,
                max_filings=max_filings,
            )

            if result.get("status") == "success":
                _ingested_symbols.add(cache_key)
                logger.info(
                    "Ingested {} chunks for {} (types: {}).",
                    result.get("chunks_ingested", 0),
                    symbol,
                    result.get("filing_types"),
                )
                return True

            logger.warning(
                "No RAG data ingested for {} (status={}).",
                symbol,
                result.get("status"),
            )
            return False

        except Exception as exc:
            logger.warning(
                "RAG ingestion failed for {}: {}. Continuing without RAG.",
                symbol,
                exc,
            )
            self._rag_enabled = False
            return False

    # ------------------------------------------------------------------
    # Context retrieval
    # ------------------------------------------------------------------

    def get_rag_context(
        self,
        symbol: str,
        queries: List[str],
        filing_types: Optional[List[str]] = None,
        max_context_chars: int = 6000,
    ) -> str:
        """Retrieve relevant document context for *symbol* across *queries*.

        Gathers context from ``get_filing_context`` for each query and
        concatenates the results into a single string suitable for
        injection into an LLM prompt.

        Args:
            symbol: Stock ticker (e.g., ``"AAPL"``).
            queries: List of natural-language queries to search for.
            filing_types: Optional list of filing types to filter by
                (e.g., ``["10-K"]``).  If ``None``, all filing types
                are searched.
            max_context_chars: Maximum characters per individual query
                result.

        Returns:
            A formatted context string.  Returns an empty string if RAG
            is disabled or no results are found.
        """
        if not self._rag_enabled:
            return ""

        symbol = symbol.upper()
        context_parts: List[str] = []

        try:
            from src.tools.document_search import get_filing_context, search_transcripts

            # Gather filing context for each query.
            for query in queries:
                filing_type = filing_types[0] if filing_types and len(filing_types) == 1 else ""
                ctx = get_filing_context(
                    symbol=symbol,
                    query=query,
                    filing_type=filing_type,
                    max_context_chars=max_context_chars,
                )
                if ctx and ctx.strip():
                    context_parts.append(ctx.strip())

            # Also search earnings transcripts for each query.
            for query in queries:
                try:
                    transcript_result = search_transcripts(
                        symbol=symbol,
                        query=query,
                        top_k=3,
                    )
                    for hit in transcript_result.get("results", []):
                        text = hit.get("text", "").strip()
                        if text:
                            meta = hit.get("metadata", {})
                            source = " ".join(
                                filter(None, [meta.get("quarter"), meta.get("year")])
                            )
                            header = f"[Earnings Transcript{' - ' + source if source else ''}]"
                            context_parts.append(f"{header}\n{text}")
                except Exception:
                    # Transcript search is best-effort.
                    pass

        except Exception as exc:
            logger.warning(
                "RAG context retrieval failed for {}: {}. Continuing without RAG context.",
                symbol,
                exc,
            )
            self._rag_enabled = False
            return ""

        if not context_parts:
            logger.debug("No RAG context found for {} with queries: {}", symbol, queries)
            return ""

        combined = "\n\n---\n\n".join(context_parts)
        logger.info(
            "Retrieved {} RAG context blocks for {} ({} chars total).",
            len(context_parts),
            symbol,
            len(combined),
        )
        return combined

    # ------------------------------------------------------------------
    # Task enrichment
    # ------------------------------------------------------------------

    def enrich_task_with_rag(
        self,
        task: str,
        symbol: str,
        queries: Optional[List[str]] = None,
        filing_types: Optional[List[str]] = None,
        max_context_chars: int = 6000,
    ) -> str:
        """Append RAG context to a task prompt string.

        If RAG is disabled or no relevant context is found the original
        *task* string is returned unchanged.

        Args:
            task: The original task/prompt string.
            symbol: Stock ticker to retrieve context for.
            queries: Explicit search queries.  If ``None``, a default
                query is derived from the first 200 characters of *task*.
            filing_types: Optional filing-type filter.
            max_context_chars: Maximum context characters per query.

        Returns:
            The (potentially enriched) task string.
        """
        if not self._rag_enabled:
            return task

        if queries is None:
            # Derive a sensible default query from the task itself.
            queries = [task[:200].strip()]

        context = self.get_rag_context(
            symbol=symbol,
            queries=queries,
            filing_types=filing_types,
            max_context_chars=max_context_chars,
        )

        if not context:
            return task

        enriched = (
            f"{task}\n\n"
            "--- Relevant Document Context (from SEC filings & earnings transcripts) ---\n\n"
            f"{context}\n\n"
            "--- End Document Context ---"
        )
        return enriched
