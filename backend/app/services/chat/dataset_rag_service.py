"""
Dataset RAG Service.

Embeds GEO dataset metadata (strategy + metrics JSON files) and provides
semantic search using cosine similarity on in-memory numpy arrays.

- Embeddings: mistral-embed via Mistral SDK (dim=1024)
- Store: numpy array + JSON metadata persisted on disk
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

import numpy as np
from mistralai import Mistral

logger = logging.getLogger(__name__)

# Directory where *.strategy.json and *.metrics.json live
DATASETS_DIR = Path(__file__).parent.parent.parent.parent / "datasets"

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
INDEX_FILE = DATA_DIR / "rag_index.json"
DOCS_FILE = DATA_DIR / "rag_docs.json"
EMBEDDINGS_FILE = DATA_DIR / "rag_embeddings.npy"


class DatasetRAGService:
    """
    In-memory semantic search over GEO dataset metadata.

    Embeddings are generated via Mistral and stored as a numpy array on disk
    so they survive restarts without re-embedding unchanged files.

    Usage:
        service = DatasetRAGService.from_env()
        await service.index_datasets()          # call once at app startup
        docs = await service.search("bladder cancer survival")
    """

    def __init__(self, mistral_key: str) -> None:
        self._mistral = Mistral(api_key=mistral_key)
        self._index: dict[str, str] = self._load_index()
        # doc_id → document dict (accession, content, metadata)
        self._docs: dict[str, dict] = {}
        # doc_id → embedding (list[float], dim=1024)
        self._emb: dict[str, list[float]] = {}
        self._load_store()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "DatasetRAGService":
        """Create service from environment variables."""
        mistral_key = os.getenv("MISTRAL_KEY", "")
        if not mistral_key:
            key_file = Path(__file__).parent.parent / "mistral_key.txt"
            if key_file.exists():
                mistral_key = key_file.read_text().strip()
        return cls(mistral_key=mistral_key)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    async def _embed(self, text: str) -> list[float]:
        """Generate a 1024-dim embedding via Mistral embed API."""
        resp = await self._mistral.embeddings.create_async(
            model="mistral-embed",
            inputs=[text],
        )
        return resp.data[0].embedding

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

        indexed = 0

        for json_file in sorted(datasets_dir.glob("*.json")):
            doc_id, doc = self._build_doc(json_file)
            if doc is None:
                continue

            file_hash = self._hash_file(json_file)
            if self._index.get(doc_id) == file_hash:
                continue  # unchanged — skip

            embedding = await self._embed(doc["content"])
            self._docs[doc_id] = doc
            self._emb[doc_id] = embedding
            self._index[doc_id] = file_hash
            indexed += 1

        if indexed == 0:
            logger.info("RAG index up-to-date — no new datasets to embed")
        else:
            self._save_store()
            self._save_index()
            logger.info(f"RAG index updated: {indexed} documents added/updated")

        return indexed

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: str, k: int = 5) -> list[dict]:
        """
        Semantic similarity search over indexed dataset metadata.

        Args:
            query: Natural-language query (e.g. "bladder cancer survival microarray")
            k: Number of results to return

        Returns:
            List of dicts with keys: accession, content, metadata
        """
        if not self._docs:
            return []

        query_emb = await self._embed(query)
        q = np.array(query_emb, dtype=np.float32)

        doc_ids = list(self._docs.keys())
        emb_matrix = np.array(
            [self._emb[did] for did in doc_ids], dtype=np.float32
        )  # shape (n, 1024)

        # Cosine similarity: (emb_matrix @ q) / (||emb_matrix|| * ||q||)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        row_norms = np.linalg.norm(emb_matrix, axis=1)
        row_norms = np.where(row_norms == 0, 1e-8, row_norms)
        sims = (emb_matrix @ q) / (row_norms * q_norm)

        top_k = min(k, len(doc_ids))
        top_idx = np.argsort(sims)[::-1][:top_k]

        return [
            {
                "accession": self._docs[doc_ids[i]]["accession"],
                "content": self._docs[doc_ids[i]]["content"],
                "metadata": self._docs[doc_ids[i]]["metadata"],
            }
            for i in top_idx
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_doc(self, json_file: Path) -> tuple[str, Optional[dict]]:
        """Build a document dict from a strategy or metrics JSON file."""
        try:
            data = json.loads(json_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Skipping {json_file.name}: {exc}")
            return json_file.stem, None

        stem = json_file.stem  # e.g. "GSE11121.strategy" or "GSE11121.metrics"
        parts = stem.split(".")
        accession = parts[0]
        file_type = parts[1] if len(parts) > 1 else "unknown"

        if file_type == "strategy":
            content = (
                f"Dataset: {accession}\n"
                f"Format: {data.get('file_format', 'unknown')}\n"
                f"Notes: {data.get('notes', '')}"
            )
        elif file_type == "metrics":
            missing = data.get("missing_rate")
            if isinstance(missing, float):
                content = (
                    f"Dataset: {accession}\n"
                    f"Genes: {data.get('n_genes', 'unknown')}\n"
                    f"Samples: {data.get('n_samples', 'unknown')}\n"
                    f"Missing rate: {missing:.3f}"
                )
            else:
                content = f"Dataset: {accession} metrics: {json.dumps(data)}"
        else:
            content = f"Dataset: {accession}\n{json.dumps(data)}"

        doc_id = f"{accession}_{file_type}"
        return doc_id, {
            "accession": accession,
            "content": content,
            "metadata": {"accession": accession, "type": file_type, **data},
        }

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
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(json.dumps(self._index, indent=2))

    def _load_store(self) -> None:
        """Load persisted documents and embeddings from disk."""
        if not DOCS_FILE.exists() or not EMBEDDINGS_FILE.exists():
            return
        try:
            docs_list: list[dict] = json.loads(DOCS_FILE.read_text())
            emb_array = np.load(str(EMBEDDINGS_FILE), allow_pickle=False)
            for i, entry in enumerate(docs_list):
                doc_id = entry.pop("_id")
                self._docs[doc_id] = entry
                self._emb[doc_id] = emb_array[i].tolist()
            logger.info(f"RAG store loaded: {len(self._docs)} documents")
        except (OSError, ValueError, KeyError) as exc:
            logger.warning(f"Failed to load RAG store, will rebuild: {exc}")
            self._docs = {}
            self._emb = {}

    def _save_store(self) -> None:
        """Persist documents and embeddings to disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        doc_ids = list(self._docs.keys())
        docs_list = [{"_id": did, **self._docs[did]} for did in doc_ids]
        emb_array = np.array(
            [self._emb[did] for did in doc_ids], dtype=np.float32
        )
        DOCS_FILE.write_text(json.dumps(docs_list))
        np.save(str(EMBEDDINGS_FILE), emb_array)
