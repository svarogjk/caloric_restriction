---
name: geo-platform-streaming
description: Streaming download of large GEO GPL platform annotation files. Use when downloading GPL platforms with multi-GB SOFT files (e.g. GPL5175=4.3GB, GPL5188=41.5GB). Downloads only the platform table section (~14-36MB) instead of full file. Output: parquet with probe_id + gene_symbol columns.
---

# GEO Platform Streaming Download

## Key Insight

GEO SOFT files are structured text with a platform annotation table delimited by:
```
!platform_table_begin
<header row>
<data rows>
!platform_table_end
<rest of file — megabytes/gigabytes of sample data we don't need>
```

**Close the HTTP stream immediately after `!platform_table_end`** to avoid downloading gigabytes of irrelevant sample data.

## Real-world impact

| Platform | Full file size | Bytes actually downloaded | Rows extracted | Time |
|----------|---------------|--------------------------|----------------|------|
| GPL5175  | 4,319 MB      | 14 MB                    | 78,907         | 9s   |
| GPL5188  | 41,553 MB     | 36.5 MB                  | 620,000        | 13s  |

## Output Format

Parquet file at `platform_mappings/GPL{id}_gene_mapping.parquet`:
```
probe_id       object
gene_symbol    object
```
Identical schema to all other pre-built platform parquets used by `gene_mapping_service.py`.

## URL Pattern

```python
def _soft_url(platform_id: str) -> str:
    num = int(platform_id)
    prefix = f"GPL{(num // 1000)}nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{prefix}/GPL{platform_id}/soft/GPL{platform_id}_family.soft.gz"

def _annot_url(platform_id: str) -> str:
    # annot files are smaller — try first, fall back to soft
    num = int(platform_id)
    prefix = f"GPL{(num // 1000)}nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{prefix}/GPL{platform_id}/annot/GPL{platform_id}.annot.gz"
```

Always try the `.annot.gz` URL first (much smaller). Fall back to `_family.soft.gz` on 404.

## Incremental gzip Decompressor

SOFT files are gzip-compressed. Use `zlib.decompressobj(wbits=47)` to decompress streaming chunks without buffering the full file:

```python
import zlib

class StreamingDecompressor:
    def __init__(self):
        # wbits=47 → auto-detect zlib/gzip
        self._d = zlib.decompressobj(wbits=47)

    def decompress(self, data: bytes) -> bytes:
        return self._d.decompress(data)
```

## Full Streaming Parser

```python
import gzip, re, zlib
from typing import Optional
import httpx
import pandas as pd
from pathlib import Path

CACHE_DIR = Path("platform_mappings")
ID_NAMES = {"id", "probe_id", "probeset_id", "probe", "id_ref"}
GENE_KEYWORDS = ["gene", "symbol", "mrna", "assignment", "annotation"]


def stream_parse_platform(platform_id: str) -> Optional[pd.DataFrame]:
    """Stream-parse GPL SOFT file: only download the platform table section."""
    urls = [_annot_url(platform_id), _soft_url(platform_id)]

    for url in urls:
        try:
            with httpx.stream("GET", url, timeout=None, follow_redirects=True) as resp:
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                result = _parse_stream(resp.iter_bytes(chunk_size=512 * 1024))
                if result is not None:
                    return result
        except httpx.HTTPStatusError:
            continue
    return None


def _parse_stream(byte_iter) -> Optional[pd.DataFrame]:
    decompressor = zlib.decompressobj(wbits=47)
    tail = b""
    in_table = False
    header_parsed = False
    id_col: Optional[int] = None
    gene_cols: list[int] = []
    mappings: dict[str, str] = {}

    for raw_chunk in byte_iter:
        text_data = decompressor.decompress(raw_chunk)
        combined = tail + text_data
        lines = combined.split(b"\n")
        tail = lines[-1]

        for raw_line in lines[:-1]:
            line = raw_line.decode("utf-8", errors="replace").rstrip()

            if line.startswith("!platform_table_begin"):
                in_table = True
                continue

            if line.startswith("!platform_table_end"):
                # ← Close connection here, stop downloading
                return pd.DataFrame(list(mappings.items()), columns=["probe_id", "gene_symbol"])

            if not in_table or line.startswith("!"):
                continue

            if not header_parsed:
                columns = [c.strip().strip('"') for c in line.split("\t")]
                id_col = next((i for i, c in enumerate(columns)
                               if c.strip("#").strip().lower() in ID_NAMES), None)
                gene_cols = [i for i, c in enumerate(columns)
                             if any(kw in c.lower() for kw in GENE_KEYWORDS)]
                if id_col is None or not gene_cols:
                    return None
                header_parsed = True
                continue

            fields = line.split("\t")
            if len(fields) > id_col:
                probe_id = fields[id_col].strip()
                if probe_id:
                    gene = _extract_gene_from_fields(fields, gene_cols)
                    if gene:
                        mappings[probe_id] = gene

    return pd.DataFrame(list(mappings.items()), columns=["probe_id", "gene_symbol"]) if mappings else None


def _extract_gene_from_fields(fields: list[str], gene_col_indices: list[int]) -> Optional[str]:
    for idx in gene_col_indices:
        if idx < len(fields):
            gene = _extract_gene(fields[idx])
            if gene:
                return gene
    return None


def _extract_gene(text: str) -> Optional[str]:
    if not text or text.strip() in {"---", "NA", "NULL", "", "null", "N/A"}:
        return None
    text = text.strip()
    # Symbol in parentheses: "description (SYMBOL)"
    m = re.search(r"\(([A-Za-z0-9_\-]+)\)", text)
    if m and re.match(r"^[A-Z][A-Za-z0-9_\-]*$", m.group(1)):
        return m.group(1)
    # First token before delimiters
    text = re.split(r"\s*///\s*|[;,|/]", text)[0].strip()
    text = re.sub(r"\s*\[.*?\]", "", text).strip().strip('"').strip("'")
    if text and re.match(r"^[A-Za-z0-9][A-Za-z0-9_\-\.]*$", text):
        return text
    return None
```

## CLI Script

The ready-to-run script lives at `backend/download_large_platforms.py`:

```bash
# Download specific platform IDs
uv run python download_large_platforms.py 5175 5188

# Default targets (GPL5175, GPL5188) if no args given
uv run python download_large_platforms.py
```

Skips platforms that already have a parquet. Saves to `platform_mappings/GPL{id}_gene_mapping.parquet`.

## When to Use This

- When `gene_mapping_service.py` logs a platform with size `> 500 MB` in the pre-download check
- When `download_platforms.py` would take hours or OOM for a platform
- Specifically confirmed necessary for: GPL5175, GPL5188, GPL16686, GPL23159, GPL4133

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `OSError` in decompressor | Server returned non-gzip | Treat bytes as plain text |
| No `!platform_table_end` found | Some files lack the marker | Use collected mappings anyway |
| Empty gene columns | Unusual column names | Inspect first few columns, add keyword |
| 404 on annot URL | No annot file for this platform | Falls back to soft automatically |
