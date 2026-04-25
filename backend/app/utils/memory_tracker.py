"""
Lightweight memory consumption tracker for GEO analysis workloads.

Uses psutil to read process RSS at key checkpoints, logging deltas so
peak memory can be observed in geo_logs/geo_analysis.log without any
background polling thread.

All log lines begin with a "MEM " prefix for easy grep:
  grep "MEM " geo_logs/geo_analysis.log
  grep "MEM SUMMARY" geo_logs/geo_analysis.log
  grep "MEM END" geo_logs/geo_analysis.log | sort -t= -k3 -rn | head -20
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import psutil

from app.config.logging_config import get_logger

logger = get_logger(__name__)

# Single cached Process object — avoids repeated pid lookup on every call.
# psutil.Process.memory_info() reads /proc/self/status on Linux (~0.1 ms, atomic).
_proc: psutil.Process = psutil.Process()

# Module-level peak RSS tracker.  Written only when a new high-water mark is found.
_peak_rss_mb: float = 0.0
_peak_lock: asyncio.Lock = asyncio.Lock()


def _rss_mb() -> float:
    """Return current process RSS in MB.  Safe to call from sync or async code."""
    return _proc.memory_info().rss / (1024 * 1024)


async def _update_peak(current_mb: float) -> None:
    """Update global peak with double-checked locking (asyncio-safe)."""
    global _peak_rss_mb
    if current_mb > _peak_rss_mb:
        async with _peak_lock:
            if current_mb > _peak_rss_mb:
                _peak_rss_mb = current_mb


@asynccontextmanager
async def track_memory(
    operation: str,
    context_id: Optional[str] = None,
) -> AsyncIterator[None]:
    """
    Async context manager that logs RSS before and after the wrapped block.

    Example::

        async with track_memory("load_dataset", context_id=accession):
            loaded_data = await loader.load(...)

    Produces two log lines::

        MEM START  load_dataset[GSE19188]    rss=  312.4 MB
        MEM END    load_dataset[GSE19188]    rss=  589.1 MB  delta=+276.7 MB  elapsed=5.83s
    """
    tag = f"{operation}[{context_id}]" if context_id else operation
    before = _rss_mb()
    t0 = time.perf_counter()

    logger.info("MEM START  %-55s rss=%6.1f MB", tag, before)

    try:
        yield
    finally:
        after = _rss_mb()
        delta = after - before
        elapsed = time.perf_counter() - t0
        await _update_peak(after)

        sign = "+" if delta >= 0 else ""
        logger.info(
            "MEM END    %-55s rss=%6.1f MB  delta=%s%.1f MB  elapsed=%.2fs",
            tag, after, sign, delta, elapsed,
        )


def log_memory_checkpoint(
    operation: str,
    context_id: Optional[str] = None,
) -> float:
    """
    Single-shot memory checkpoint — no paired call required.
    Returns current RSS in MB so callers can compute their own deltas.

    Example::

        log_memory_checkpoint("expression_matrix_sliced", accession)
    """
    rss = _rss_mb()
    tag = f"{operation}[{context_id}]" if context_id else operation
    logger.info("MEM CHECK  %-55s rss=%6.1f MB", tag, rss)
    return rss


def log_analysis_summary(
    query: str,
    n_datasets: int,
    n_genes: int,
    processing_time: float,
) -> None:
    """
    Emit a one-line summary after a complete analysis workflow, including
    the session peak RSS and total elapsed time.

    Example output::

        MEM SUMMARY  query='lung cancer survival'  datasets=8  genes=47
                     peak_rss=871.3 MB  elapsed=182.4s
    """
    logger.info(
        "MEM SUMMARY  query=%r  datasets=%d  genes=%d  peak_rss=%.1f MB  elapsed=%.1fs",
        query, n_datasets, n_genes, _peak_rss_mb, processing_time,
    )
