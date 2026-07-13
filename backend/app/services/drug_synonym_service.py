"""Drug synonym resolution via PubChem (NCBI/NLM), used to widen drug-name
matching for the "Treatments to consider" cohort-KM lookups (F24b).

GEO sample-characteristics fields and DGIdb/CIViC drug strings frequently use
different names for the same compound (generic name, brand name, research
code — e.g. "belinostat" vs "PXD101" vs "Beleodaq"). A literal string match
against only the DGIdb/CIViC-reported name silently misses real,
already-downloaded cohort data. PubChem PUG-REST provides free, keyless
synonym lookups; results are cached to disk since synonyms are static
chemical facts (no TTL needed).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parents[2] / "platform_mappings" / ".drug_synonym_cache.json"
_CACHE_MAX = 500
_MAX_SYNONYMS = 8
_MAX_SYNONYM_LEN = 40
_CAS_NUMBER_PATTERN = re.compile(r"^\d+-\d+-\d+$")
_RATE_LIMIT_DELAY = 0.25  # ~4 req/s, under PubChem's recommended 5 req/s


def _is_usable_synonym(name: str, drug_name: str) -> bool:
    if not name or len(name) > _MAX_SYNONYM_LEN:
        return False
    if _CAS_NUMBER_PATTERN.match(name):
        return False
    if name.strip().lower() == drug_name.strip().lower():
        return False
    return True


class DrugSynonymService:
    """Looks up alternate names for a drug via PubChem PUG-REST, with a
    disk-persisted LRU cache (per project convention, cache files live under
    `backend/platform_mappings/`, never `/tmp`)."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self) -> None:
        self._cache: "OrderedDict[str, List[str]]" = OrderedDict()
        self._load_cache()
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        self.client = httpx.AsyncClient(timeout=15.0)

    def _load_cache(self) -> None:
        try:
            if _CACHE_PATH.exists():
                with open(_CACHE_PATH, "r") as f:
                    data = json.load(f)
                self._cache = OrderedDict(data)
                logger.debug("Loaded %d cached drug synonym entries", len(self._cache))
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Could not load drug synonym cache: %s", e)

    def _save_cache(self) -> None:
        try:
            _CACHE_PATH.parent.mkdir(exist_ok=True)
            with open(_CACHE_PATH, "w") as f:
                json.dump(dict(self._cache), f)
        except OSError as e:
            logger.debug("Could not save drug synonym cache: %s", e)

    def _cache_put(self, key: str, value: List[str]) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > _CACHE_MAX:
            self._cache.popitem(last=False)
        self._save_cache()

    async def _rate_limit(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < _RATE_LIMIT_DELAY:
                await asyncio.sleep(_RATE_LIMIT_DELAY - elapsed)
            self._last_request_time = time.monotonic()

    async def get_synonyms(self, drug_name: str) -> List[str]:
        """Return up to `_MAX_SYNONYMS` alternate names for `drug_name`
        (brand names, research codes, etc.), filtered of noisy IUPAC/CAS
        entries. Returns `[]` on any lookup failure — callers should still
        try matching against the bare drug name."""
        key = drug_name.strip().lower()
        if not key:
            return []
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        await self._rate_limit()
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/compound/name/{drug_name}/synonyms/JSON"
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data["InformationList"]["Information"][0]["Synonym"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            logger.debug("PubChem synonym lookup failed for %s: %s", drug_name, e)
            self._cache_put(key, [])
            return []

        synonyms = [s for s in raw if _is_usable_synonym(s, drug_name)][:_MAX_SYNONYMS]
        self._cache_put(key, synonyms)
        return synonyms


_service: Optional[DrugSynonymService] = None


def get_drug_synonym_service() -> DrugSynonymService:
    global _service
    if _service is None:
        _service = DrugSynonymService()
    return _service
