---
name: geo-platform-streaming
description: Streaming download and parsing of large GEO GPL platform SOFT files to extract probe_id → gene_symbol mappings. Use when a platform file exceeds ~200MB — streams only the platform table section, closing the connection immediately after it ends. Reduces download from GB to MB.
---

# GEO Platform Streaming Download Skill

You are an expert at efficiently extracting probe-to-gene mappings from NCBI GEO platform annotation files without downloading entire multi-gigabyte SOFT files.

## Core Concept

GEO SOFT files embed the platform annotation table inline, delimited by:

```
!platform_table_begin
ID    GB_LIST    GENE_SYMBOL    ...
<data rows>
!platform_table_end
<everything below = sample data, not needed>
```

The platform table is always near the **start** of the file. Stop downloading as soon as `!platform_table_end` is seen.

### Real-world savings

| Platform | Full SOFT size | Actually downloaded | Mappings | Time |
|----------|---------------|---------------------|----------|------|
| GPL5175  | 4,319 MB      | **14 MB**           | 78,907   | 9s   |
| GPL5188  | 41,553 MB     | **36.5 MB**         | 620,000  | 13s  |

## URL Construction

```python
def _soft_url(platform_id: str) -> str:
    prefix = f"GPL{int(platform_id) // 1000}nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{prefix}/GPL{platform_id}/soft/GPL{platform_id}_family.soft.gz"

def _annot_url(platform_id: str) -> str:
    # Prefer annot (smaller), fall back to soft on 404
    prefix = f"GPL{int(platform_id) // 1000}nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{prefix}/GPL{platform_id}/annot/GPL{platform_id}.annot.gz"
```

## Streaming Implementation

### Incremental Gzip Decompressor

```python
import zlib

class StreamingDecompressor:
    """Decompress gzip data chunk-by-chunk without buffering the full stream."""
    def __init__(self):
        self._d = zlib.decompressobj(wbits=47)  # 47 = auto-detect zlib/gzip

    def decompress(self, data: bytes) -> bytes:
        return self._d.decompress(data)
```

### Full Parser

```python
import re
from typing import Optional
import httpx
import pandas as pd
from pathlib import Path

CACHE_DIR = Path("platform_mappings")
ID_NAMES = {"id", "probe_id", "probeset_id", "probe", "id_ref"}
GENE_KEYWORDS = ["gene", "symbol", "mrna", "assignment", "annotation"]


def download_platform_mapping(platform_id: str) -> Optional[pd.DataFrame]:
    """
    Stream-parse a GEO GPL platform file.
    Returns DataFrame(probe_id, gene_symbol) or None on failure.
    Downloads only the platform table section (~14-36MB), not the full file.
    """
    for url in [_annot_url(platform_id), _soft_url(platform_id)]:
        try:
            with httpx.stream("GET", url, timeout=None, follow_redirects=True) as resp:
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()

                decompressor = zlib.decompressobj(wbits=47)
                tail = b""
                in_table = False
                header_parsed = False
                id_col: Optional[int] = None
                gene_cols: list[int] = []
                mappings: dict[str, str] = {}

                for raw_chunk in resp.iter_bytes(chunk_size=512 * 1024):
                    combined = tail + decompressor.decompress(raw_chunk)
                    lines = combined.split(b"\n")
                    tail = lines[-1]

                    for raw_line in lines[:-1]:
                        line = raw_line.decode("utf-8", errors="replace").rstrip()

                        if line.startswith("!platform_table_begin"):
                            in_table = True
                            continue

                        if line.startswith("!platform_table_end"):
                            # ← Stop here — connection closes when context exits
                            return pd.DataFrame(
                                list(mappings.items()),
                                columns=["probe_id", "gene_symbol"]
                            )

                        if not in_table or line.startswith("!"):
                            continue

                        if not header_parsed:
                            cols = [c.strip().strip('"') for c in line.split("\t")]
                            id_col = next(
                                (i for i, c in enumerate(cols)
                                 if c.strip("#").strip().lower() in ID_NAMES), None
                            )
                            gene_cols = [
                                i for i, c in enumerate(cols)
                                if any(kw in c.lower() for kw in GENE_KEYWORDS)
                            ]
                            if id_col is None or not gene_cols:
                                break  # Try next URL
                            header_parsed = True
                            continue

                        fields = line.split("\t")
                        if id_col is not None and len(fields) > id_col:
                            probe_id = fields[id_col].strip()
                            if probe_id:
                                gene = _extract_gene(fields, gene_cols)
                                if gene:
                                    mappings[probe_id] = gene

        except httpx.HTTPStatusError:
            continue

    return None


def _extract_gene(fields: list[str], gene_col_indices: list[int]) -> Optional[str]:
    for idx in gene_col_indices:
        if idx >= len(fields):
            continue
        text = fields[idx].strip()
        if not text or text in {"---", "NA", "NULL", "", "null", "N/A"}:
            continue
        # Symbol in parentheses: "full description (SYMBOL)"
        m = re.search(r"\(([A-Za-z0-9_\-]+)\)", text)
        if m and re.match(r"^[A-Z][A-Za-z0-9_\-]*$", m.group(1)):
            return m.group(1)
        # First delimiter-separated token
        text = re.split(r"\s*///\s*|[;,|/]", text)[0].strip()
        text = re.sub(r"\s*\[.*?\]", "", text).strip().strip('"').strip("'")
        if text and re.match(r"^[A-Za-z0-9][A-Za-z0-9_\-\.]*$", text):
            return text
    return None
```

## Saving to Parquet

Output must match the schema used by `gene_mapping_service.py`:

```python
def save_platform_mapping(platform_id: str, df: pd.DataFrame) -> Path:
    """Save probe→gene mapping in the format expected by gene_mapping_service."""
    out_path = CACHE_DIR / f"GPL{platform_id}_gene_mapping.parquet"
    df.to_parquet(out_path, index=False)
    return out_path
```

**Schema:**
```
probe_id       object   # e.g. "2315100", "ILMN_1343291"
gene_symbol    object   # e.g. "TP53", "NR_024005"
```

## CLI Usage

```bash
# Script: backend/download_large_platforms.py
uv run python download_large_platforms.py 5175 5188

# Processes GPL5175 then GPL5188, skips if parquet already exists
```

## When Not to Use This

- Platforms already in `platform_mappings/` as `.parquet` → already cached
- Small platforms (<200 MB) → `download_platforms.py` handles them fine
- Sequencing platforms (no probe mappings) → skip entirely

## Known Large Platforms Requiring This Approach

| GPL ID | Common Datasets | Full Size |
|--------|----------------|-----------|
| GPL5175 | GSE111477, GSE109169 | 4,319 MB |
| GPL5188 | GSE111477 | 41,553 MB |
| GPL16686 | GSE143626 | 3,607 MB |
| GPL23159 | GSE147471 | 1,490 MB |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `OSError` in decompressor | Server returned plain text | Treat bytes as-is |
| No `!platform_table_end` | Some files omit it | Use collected mappings |
| Zero gene cols detected | Unusual column names | Log first 10 columns, extend `GENE_KEYWORDS` |
| 404 on annot URL | No `.annot.gz` for platform | Script auto-falls back to `.soft.gz` |
