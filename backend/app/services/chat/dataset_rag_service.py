"""
Dataset RAG Service.

Embeds GEO dataset metadata (strategy + metrics JSON files) into a pgvector
store so the chat agent can perform semantic search over known datasets.

- Embeddings: MistralAIEmbeddings("mistral-embed", dim=1024)
- Store: PGVector via langchain-postgres (psycopg3 driver)
- Idempotency: hash-based — only re-embeds files that have changed
- Embedding model is always Mistral regardless of which chat LLM is active
  (Anthropic has no embedding API)
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_mistralai import MistralAIEmbeddings
from langchain_postgres import PGVector

logger = logging.getLogger(__name__)

# Directory where *.strategy.json and *.metrics.json live
DATASETS_DIR = Path(__file__).parent.parent.parent.parent / "datasets"

# Persisted index so we don't re-embed unchanged files across restarts
INDEX_FILE = Path(__file__).parent.parent.parent.parent / "data" / "rag_index.json"


class DatasetRAGService:
    """
    Manages pgvector-backed semantic search over GEO dataset metadata.

    Usage:
        service = DatasetRAGService.from_env()
        await service.index_datasets()          # call once at app startup
        docs = await service.search("bladder cancer survival")
    """

    COLLECTION = "geo_datasets"

    def __init__(self, connection_string: str, mistral_key: str) -> None:
        self.embeddings = MistralAIEmbeddings(
            api_key=mistral_key,
            model="mistral-embed",
        )
        self.store = PGVector(
            embeddings=self.embeddings,
            collection_name=self.COLLECTION,
            connection=connection_string,
            use_jsonb=True,
            async_mode=True,
        )
        self._index: dict[str, str] = self._load_index()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "DatasetRAGService":
        """Create service from environment variables."""
        raw_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://geo_user:geo_password@localhost:5432/geo_chat",
        )
        # langchain-postgres async methods require psycopg3 async driver
        psycopg_url = raw_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg_async://"
        )

        mistral_key = os.getenv("MISTRAL_KEY", "")
        if not mistral_key:
            key_file = Path(__file__).parent.parent.parent / "services" / "mistral_key.txt"
            if key_file.exists():
                mistral_key = key_file.read_text().strip()

        return cls(connection_string=psycopg_url, mistral_key=mistral_key)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    async def index_datasets(self, datasets_dir: Optional[Path] = None) -> int:
        """
        Embed and store dataset JSON files that have changed since last run.

        Returns:
            Number of documents newly indexed.
        """
        datasets_dir = datasets_dir or DATASETS_DIR
        if not datasets_dir.exists():
            logger.warning(f"Datasets directory not found: {datasets_dir}")
            return 0

        docs_to_add: list[Document] = []
        ids_to_add: list[str] = []

        for json_file in sorted(datasets_dir.glob("*.json")):
            doc_id, document = self._build_document(json_file)
            if document is None:
                continue

            file_hash = self._hash_file(json_file)
            if self._index.get(doc_id) == file_hash:
                continue  # unchanged — skip

            docs_to_add.append(document)
            ids_to_add.append(doc_id)
            self._index[doc_id] = file_hash

        if not docs_to_add:
            logger.info("RAG index up-to-date — no new datasets to embed")
            return 0

        logger.info(f"Embedding {len(docs_to_add)} dataset documents into pgvector...")
        await self.store.aadd_documents(docs_to_add, ids=ids_to_add)
        self._save_index()
        logger.info(f"RAG index updated: {len(docs_to_add)} documents added")
        return len(docs_to_add)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: str, k: int = 5) -> list[Document]:
        """
        Semantic similarity search over indexed dataset metadata.

        Args:
            query: Natural-language query (e.g. "bladder cancer survival microarray")
            k: Number of results to return

        Returns:
            List of matching Documents with metadata (accession, n_samples, etc.)
        """
        return await self.store.asimilarity_search(query, k=k)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_document(
        self, json_file: Path
    ) -> tuple[str, Optional[Document]]:
        """Build a LangChain Document from a strategy or metrics JSON file."""
        try:
            data = json.loads(json_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Skipping {json_file.name}: {exc}")
            return json_file.stem, None

        stem = json_file.stem  # e.g. "GSE11121.strategy" or "GSE11121.metrics"
        parts = stem.split(".")
        accession = parts[0]  # e.g. "GSE11121"
        file_type = parts[1] if len(parts) > 1 else "unknown"

        if file_type == "strategy":
            content = (
                f"Dataset: {accession}\n"
                f"Format: {data.get('file_format', 'unknown')}\n"
                f"Notes: {data.get('notes', '')}"
            )
        elif file_type == "metrics":
            content = (
                f"Dataset: {accession}\n"
                f"Genes: {data.get('n_genes', 'unknown')}\n"
                f"Samples: {data.get('n_samples', 'unknown')}\n"
                f"Missing rate: {data.get('missing_rate', 'unknown'):.3f}"
                if isinstance(data.get("missing_rate"), float)
                else f"Dataset: {accession} metrics: {json.dumps(data)}"
            )
        else:
            content = f"Dataset: {accession}\n{json.dumps(data)}"

        doc_id = f"{accession}_{file_type}"
        return doc_id, Document(
            page_content=content,
            metadata={"accession": accession, "type": file_type, **data},
        )

    @staticmethod
    def _hash_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _load_index(self) -> dict[str, str]:
        """Load the persisted hash index from disk."""
        if INDEX_FILE.exists():
            try:
                return json.loads(INDEX_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_index(self) -> None:
        """Persist the hash index to disk."""
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(json.dumps(self._index, indent=2))
