#!/usr/bin/env python3
"""
Stream-parse large GPL platform SOFT files for probe_id → gene_symbol mappings.

Strategy: stream the gzip SOFT file, parse the platform table on the fly,
then close the connection immediately after !platform_table_end is found.
This avoids downloading GB of data after the table is complete.

Output: platform_mappings/GPL{id}_gene_mapping.parquet
        with columns (probe_id: str, gene_symbol: str)
"""

import gzip
import io
import re
import sys
import time
from pathlib import Path
from typing import Optional
import httpx
import pandas as pd

CACHE_DIR = Path(__file__).parent / "platform_mappings"
BASE_URL = "https://ftp.ncbi.nlm.nih.gov/geo/platforms"

# Platforms to download  (only those not already cached)
TARGET_PLATFORMS = ["5175", "5188"]


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _soft_url(platform_id: str) -> str:
    num = int(platform_id)
    prefix = f"GPL{(num // 1000)}nnn"
    return f"{BASE_URL}/{prefix}/GPL{platform_id}/soft/GPL{platform_id}_family.soft.gz"


def _annot_url(platform_id: str) -> str:
    num = int(platform_id)
    prefix = f"GPL{(num // 1000)}nnn"
    return f"{BASE_URL}/{prefix}/GPL{platform_id}/annot/GPL{platform_id}.annot.gz"


# ---------------------------------------------------------------------------
# Gene-symbol extraction (same logic as download_platforms.py)
# ---------------------------------------------------------------------------

def _extract_gene(text: str) -> Optional[str]:
    if not text or text.strip() in {"---", "NA", "NULL", "", "null", "N/A"}:
        return None

    text = text.strip()

    # Symbol in parentheses: "description (Symbol)"
    m = re.search(r"\(([A-Za-z0-9_\-]+)\)", text)
    if m and re.match(r"^[A-Z][A-Za-z0-9_\-]*$", m.group(1)):
        return m.group(1)

    # First token before /// or ; or ,
    text = re.split(r"\s*///\s*|[;,|/]", text)[0].strip()
    text = re.sub(r"\s*\[.*?\]", "", text).strip().strip('"').strip("'")

    if text and re.match(r"^[A-Za-z0-9][A-Za-z0-9_\-\.]*$", text):
        return text

    return None


def _best_gene_from_fields(fields: list[str], gene_col_indices: list[int]) -> Optional[str]:
    for idx in gene_col_indices:
        if idx < len(fields):
            gene = _extract_gene(fields[idx])
            if gene:
                return gene
    return None


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

ID_NAMES = {"id", "probe_id", "probeset_id", "probe", "id_ref"}
GENE_KEYWORDS = ["gene", "symbol", "mrna", "assignment", "annotation"]


def _find_columns(columns: list[str]) -> tuple[Optional[int], list[int]]:
    id_col = None
    gene_cols = []

    for i, col in enumerate(columns):
        clean = col.strip("#").strip().lower()
        if clean in ID_NAMES:
            id_col = i
            break

    for i, col in enumerate(columns):
        if any(kw in col.lower() for kw in GENE_KEYWORDS):
            gene_cols.append(i)

    return id_col, gene_cols


# ---------------------------------------------------------------------------
# Core streaming parser
# ---------------------------------------------------------------------------

def stream_parse_platform(platform_id: str) -> Optional[pd.DataFrame]:
    """
    Stream the platform SOFT file, extract the platform table, return DataFrame.
    Tries annot file first (smaller), falls back to soft file.
    Connection is closed immediately after !platform_table_end.
    """
    urls_to_try = [_annot_url(platform_id), _soft_url(platform_id)]

    for url in urls_to_try:
        print(f"  Trying: {url}")

        try:
            with httpx.stream("GET", url, timeout=None, follow_redirects=True) as resp:
                if resp.status_code == 404:
                    print(f"  → 404 Not Found, skipping")
                    continue

                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                print(
                    f"  → HTTP {resp.status_code}, "
                    f"size: {total / 1024 / 1024:.1f} MB" if total else "  → HTTP 200"
                )

                # We decompress on the fly using a streaming buffer
                result = _parse_stream(resp.iter_bytes(chunk_size=512 * 1024), platform_id)

                if result is not None:
                    return result

        except httpx.HTTPStatusError as exc:
            print(f"  → HTTP error {exc.response.status_code}")
            continue

    return None


def _parse_stream(byte_iter, platform_id: str) -> Optional[pd.DataFrame]:
    """
    Feed raw gzip chunks into an incremental decompressor, parse SOFT table.
    Returns as soon as !platform_table_end is seen.
    """
    decompressor = zlib_decompressor()
    tail = b""                  # leftover bytes from previous chunk
    in_table = False
    header_parsed = False
    id_col: Optional[int] = None
    gene_cols: list[int] = []
    mappings: dict[str, str] = {}
    rows_read = 0
    bytes_received = 0

    try:
        for raw_chunk in byte_iter:
            bytes_received += len(raw_chunk)

            # Decompress chunk
            try:
                text_data = decompressor.decompress(raw_chunk)
            except OSError:
                # Some servers send non-gzip; try treating as plain text
                text_data = raw_chunk

            # Combine with leftover and split into lines
            combined = tail + text_data
            lines = combined.split(b"\n")
            tail = lines[-1]    # may be incomplete line

            for raw_line in lines[:-1]:
                try:
                    line = raw_line.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    continue

                if line.startswith("!platform_table_begin"):
                    in_table = True
                    continue

                if line.startswith("!platform_table_end"):
                    mb = bytes_received / 1024 / 1024
                    print(
                        f"\n  ✓ Table complete after {mb:.1f} MB received, "
                        f"{rows_read:,} rows → {len(mappings):,} mappings"
                    )
                    return _to_dataframe(mappings)

                if not in_table:
                    continue

                if not header_parsed:
                    columns = [c.strip().strip('"') for c in line.split("\t")]
                    id_col, gene_cols = _find_columns(columns)
                    print(f"\n  Columns: {columns[:6]}{'...' if len(columns) > 6 else ''}")
                    print(f"  ID col index: {id_col}, Gene col indices: {gene_cols}")
                    if id_col is None or not gene_cols:
                        print("  ✗ Could not identify required columns")
                        return None
                    header_parsed = True
                    continue

                # Data row
                if line.startswith("!"):
                    continue

                fields = line.split("\t")
                if len(fields) > id_col:
                    probe_id = fields[id_col].strip()
                    if probe_id:
                        gene = _best_gene_from_fields(fields, gene_cols)
                        if gene:
                            mappings[probe_id] = gene
                    rows_read += 1

                if rows_read % 50_000 == 0 and rows_read > 0:
                    mb = bytes_received / 1024 / 1024
                    print(
                        f"\r  {mb:.0f} MB received | {rows_read:,} rows | "
                        f"{len(mappings):,} mappings",
                        end="",
                        flush=True,
                    )

    except Exception as exc:
        print(f"\n  ✗ Parse error: {exc}")
        return None

    # Fell off the end without finding table_end (some files lack the marker)
    if mappings:
        print(f"\n  ⚠ No !platform_table_end found, using {len(mappings):,} mappings collected")
        return _to_dataframe(mappings)

    return None


def _to_dataframe(mappings: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        list(mappings.items()), columns=["probe_id", "gene_symbol"]
    )


# ---------------------------------------------------------------------------
# Incremental gzip decompressor (handles streaming chunks)
# ---------------------------------------------------------------------------

import zlib


class zlib_decompressor:
    """Incremental gzip decompressor for streaming chunks."""

    def __init__(self) -> None:
        # wbits=47 → auto-detect zlib/gzip
        self._d = zlib.decompressobj(wbits=47)

    def decompress(self, data: bytes) -> bytes:
        return self._d.decompress(data)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    CACHE_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("Large GPL Platform Downloader (streaming mode)")
    print("=" * 70)

    platforms = sys.argv[1:] if len(sys.argv) > 1 else TARGET_PLATFORMS

    for platform_id in platforms:
        out_path = CACHE_DIR / f"GPL{platform_id}_gene_mapping.parquet"

        print(f"\n{'=' * 70}")
        print(f"Processing GPL{platform_id}")
        print(f"{'=' * 70}")

        if out_path.exists():
            df_existing = pd.read_parquet(out_path)
            print(f"✓ Already exists: {len(df_existing):,} mappings — skipping")
            continue

        start = time.time()
        df = stream_parse_platform(platform_id)

        if df is None or df.empty:
            print(f"✗ GPL{platform_id}: no mappings extracted")
            continue

        df.to_parquet(out_path, index=False)
        elapsed = time.time() - start
        print(
            f"✓ GPL{platform_id}: {len(df):,} mappings saved to "
            f"{out_path.name} ({elapsed:.0f}s)"
        )
        time.sleep(1)

    print(f"\n{'=' * 70}")
    print("Done.")


if __name__ == "__main__":
    main()
