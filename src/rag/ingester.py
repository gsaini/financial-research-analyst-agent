"""
SEC EDGAR Document Ingester.

Fetches SEC filings (10-K, 10-Q, 8-K) from the EDGAR FULL-TEXT search API,
chunks them semantically, and stores them in ChromaDB via the Embedder.

Uses only public, free SEC EDGAR APIs — no API key required.
SEC requires a User-Agent header with contact info.

Usage::

    from src.rag.ingester import SECIngester
    ingester = SECIngester()
    count = await ingester.ingest_filings("AAPL", filing_types=["10-K", "10-Q"])
"""

from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.rag.embedder import Embedder
from src.utils.logger import get_logger

logger = get_logger(__name__)

# SEC EDGAR endpoints (free, no API key)
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FULL_TEXT_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_COMPANY_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FILING_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
EDGAR_FULL_TEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index"

# EDGAR XBRL companion API
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# SEC requires a User-Agent with contact info
SEC_HEADERS = {
    "User-Agent": "FinancialResearchAgent/1.0 (research@example.com)",
    "Accept-Encoding": "gzip, deflate",
}

# Chunk settings
CHUNK_SIZE = 512  # tokens (approximate via chars/4)
CHUNK_OVERLAP = 64


class SECIngester:
    """Fetch and ingest SEC filings into the RAG vector store."""

    def __init__(self, embedder: Optional[Embedder] = None) -> None:
        self._embedder = embedder or Embedder()
        self._client = httpx.AsyncClient(
            headers=SEC_HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

    async def close(self):
        await self._client.aclose()

    # ── Public API ───────────────────────────────────────────────

    async def ingest_filings(
        self,
        symbol: str,
        filing_types: Optional[List[str]] = None,
        max_filings: int = 5,
    ) -> int:
        """
        Fetch and ingest SEC filings for a company.

        Args:
            symbol: Stock ticker (e.g., "AAPL").
            filing_types: Filing types to fetch. Default: ["10-K", "10-Q"].
            max_filings: Max filings per type.

        Returns:
            Number of document chunks ingested.
        """
        filing_types = filing_types or ["10-K", "10-Q"]
        total_chunks = 0

        cik = await self._resolve_cik(symbol)
        if not cik:
            logger.warning(f"Could not resolve CIK for {symbol}")
            return 0

        for ft in filing_types:
            filings = await self._fetch_filing_list(cik, ft, max_filings)
            for filing in filings:
                text = await self._fetch_filing_text(filing["url"])
                if not text:
                    continue

                chunks = self._chunk_text(text)
                metadata_list = [
                    {
                        "symbol": symbol.upper(),
                        "cik": cik,
                        "filing_type": ft,
                        "filed_date": filing.get("filed", ""),
                        "accession": filing.get("accession", ""),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "source": "sec_edgar",
                    }
                    for i in range(len(chunks))
                ]

                ids = [
                    hashlib.md5(
                        f"{symbol}:{ft}:{filing.get('accession', '')}:{i}".encode()
                    ).hexdigest()
                    for i in range(len(chunks))
                ]

                self._embedder.add_documents(chunks, metadata_list, ids)
                total_chunks += len(chunks)
                logger.info(
                    f"Ingested {len(chunks)} chunks from {symbol} {ft} "
                    f"(filed {filing.get('filed', 'unknown')})"
                )

        return total_chunks

    async def ingest_text(
        self,
        text: str,
        symbol: str,
        doc_type: str = "transcript",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Ingest arbitrary text (e.g., earnings transcript) into the RAG store.

        Args:
            text: The document text.
            symbol: Stock ticker.
            doc_type: Document type label.
            metadata: Additional metadata.

        Returns:
            Number of chunks ingested.
        """
        chunks = self._chunk_text(text)
        base_meta = {
            "symbol": symbol.upper(),
            "doc_type": doc_type,
            "source": "manual",
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            base_meta.update(metadata)

        metadata_list = [{**base_meta, "chunk_index": i, "total_chunks": len(chunks)} for i in range(len(chunks))]
        ids = [
            hashlib.md5(f"{symbol}:{doc_type}:{i}:{text[:20]}".encode()).hexdigest()
            for i in range(len(chunks))
        ]

        self._embedder.add_documents(chunks, metadata_list, ids)
        logger.info(f"Ingested {len(chunks)} chunks for {symbol} ({doc_type})")
        return len(chunks)

    # ── SEC EDGAR helpers ────────────────────────────────────────

    async def _resolve_cik(self, symbol: str) -> Optional[str]:
        """Resolve a ticker symbol to a SEC CIK number."""
        try:
            resp = await self._client.get(COMPANY_TICKERS_URL)
            resp.raise_for_status()
            data = resp.json()
            for entry in data.values():
                if entry.get("ticker", "").upper() == symbol.upper():
                    cik = str(entry["cik_str"]).zfill(10)
                    return cik
        except Exception as e:
            logger.error(f"CIK resolution failed for {symbol}: {e}")
        return None

    async def _fetch_filing_list(
        self, cik: str, filing_type: str, max_filings: int
    ) -> List[Dict[str, str]]:
        """Fetch recent filing metadata from EDGAR submissions API."""
        try:
            url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])

            filings = []
            for i, form in enumerate(forms):
                if form == filing_type and len(filings) < max_filings:
                    acc_clean = accessions[i].replace("-", "")
                    doc_url = (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{cik.lstrip('0')}/{acc_clean}/{primary_docs[i]}"
                    )
                    filings.append({
                        "form": form,
                        "filed": dates[i] if i < len(dates) else "",
                        "accession": accessions[i] if i < len(accessions) else "",
                        "url": doc_url,
                    })

            return filings
        except Exception as e:
            logger.error(f"Failed to fetch filing list for CIK {cik}: {e}")
            return []

    async def _fetch_filing_text(self, url: str) -> Optional[str]:
        """Fetch and clean the text content of a filing."""
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            text = resp.text

            # Strip HTML tags for a rough plain-text extraction
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"&[a-zA-Z]+;", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            # Truncate extremely long filings (10-K can be 100k+ words)
            max_chars = 200_000  # ~50k tokens
            if len(text) > max_chars:
                text = text[:max_chars]

            return text if len(text) > 100 else None
        except Exception as e:
            logger.error(f"Failed to fetch filing from {url}: {e}")
            return None

    # ── Chunking ─────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str) -> List[str]:
        """
        Split text into overlapping chunks.

        Uses character-based splitting with ~4 chars per token heuristic.
        """
        char_size = CHUNK_SIZE * 4  # ~512 tokens
        char_overlap = CHUNK_OVERLAP * 4

        if len(text) <= char_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + char_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look back for a period/newline within overlap range
                break_zone = text[end - char_overlap : end]
                for sep in [". ", ".\n", "\n\n", "\n", "; "]:
                    last_sep = break_zone.rfind(sep)
                    if last_sep != -1:
                        end = end - char_overlap + last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - char_overlap if end < len(text) else len(text)

        return chunks
