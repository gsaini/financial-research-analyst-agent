"""
Embedding & Vector Store Manager.

Manages document embeddings and ChromaDB storage for the RAG pipeline.
Uses the embedding provider configured in ``VectorStoreSettings``.

Usage::

    from src.rag.embedder import Embedder
    embedder = Embedder()
    embedder.add_documents(texts, metadatas, ids)
    results = embedder.query("revenue growth", n_results=5)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "financial_documents"


class Embedder:
    """
    Manages embeddings and ChromaDB collection for financial documents.

    Supports multiple embedding providers:
    - sentence-transformers (default, local, free)
    - huggingface (local, free)
    - ollama (local, free)
    - openai (commercial)
    """

    def __init__(
        self,
        collection_name: str = COLLECTION_NAME,
        persist_dir: Optional[str] = None,
    ) -> None:
        from src.config import get_settings
        settings = get_settings()

        self._persist_dir = persist_dir or settings.vector_store.chroma_persist_dir
        self._collection_name = collection_name

        # Initialize embedding function
        self._embed_fn = self._create_embedding_function(settings)

        # Initialize ChromaDB
        self._client = self._create_chroma_client()
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embed_fn,
            metadata={"description": "Financial documents for RAG"},
        )

        logger.info(
            f"Embedder initialized: collection='{self._collection_name}', "
            f"persist_dir='{self._persist_dir}', "
            f"docs={self._collection.count()}"
        )

    def _create_chroma_client(self):
        """Create a persistent ChromaDB client."""
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)

        return chromadb.PersistentClient(
            path=self._persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

    def _create_embedding_function(self, settings):
        """Create the appropriate ChromaDB embedding function."""
        provider = settings.vector_store.embedding_provider.lower()

        if provider == "sentence-transformers":
            from chromadb.utils import embedding_functions
            model = settings.vector_store.sentence_transformer_model
            logger.info(f"Using Sentence Transformers embeddings: {model}")
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model,
            )
        elif provider == "openai":
            from chromadb.utils import embedding_functions
            logger.info("Using OpenAI embeddings")
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.llm.openai_api_key,
                model_name=settings.vector_store.embedding_model,
            )
        else:
            # Default to sentence-transformers
            from chromadb.utils import embedding_functions
            model = settings.vector_store.sentence_transformer_model
            logger.info(f"Defaulting to Sentence Transformers: {model}")
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model,
            )

    # ── Public API ───────────────────────────────────────────────

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """
        Add document chunks to the vector store.

        Args:
            texts: List of text chunks to embed and store.
            metadatas: Optional metadata dicts for each chunk.
            ids: Optional unique IDs. Auto-generated if not provided.
        """
        if not texts:
            return

        if ids is None:
            import hashlib
            ids = [
                hashlib.md5(f"{i}:{t[:50]}".encode()).hexdigest()
                for i, t in enumerate(texts)
            ]

        # ChromaDB has a batch limit; chunk into batches of 500
        batch_size = 500
        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            batch_texts = texts[start:end]
            batch_ids = ids[start:end]
            batch_meta = metadatas[start:end] if metadatas else None

            self._collection.upsert(
                documents=batch_texts,
                metadatas=batch_meta,
                ids=batch_ids,
            )

        logger.debug(f"Added {len(texts)} document chunks to '{self._collection_name}'")

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query the vector store for relevant document chunks.

        Args:
            query_text: The search query.
            n_results: Number of results to return.
            where: Metadata filter (e.g., {"symbol": "AAPL"}).
            where_document: Document content filter.

        Returns:
            Dict with 'documents', 'metadatas', 'distances', 'ids'.
        """
        kwargs = {
            "query_texts": [query_text],
            "n_results": min(n_results, self._collection.count() or 1),
        }
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document

        try:
            results = self._collection.query(**kwargs)
            return {
                "documents": results.get("documents", [[]])[0],
                "metadatas": results.get("metadatas", [[]])[0],
                "distances": results.get("distances", [[]])[0],
                "ids": results.get("ids", [[]])[0],
            }
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self._collection.count()

    def delete_by_symbol(self, symbol: str) -> None:
        """Delete all documents for a specific symbol."""
        try:
            self._collection.delete(where={"symbol": symbol.upper()})
            logger.info(f"Deleted all documents for {symbol}")
        except Exception as e:
            logger.error(f"Failed to delete documents for {symbol}: {e}")

    def reset(self) -> None:
        """Delete and recreate the collection (for testing)."""
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embed_fn,
        )
        logger.info(f"Reset collection '{self._collection_name}'")
