"""
Gene Mapping Service
Maps probe IDs to standardized gene symbols using GEO platform annotations
"""

import logging
import gzip
import asyncio
import json
import os
import io
from typing import Dict, Optional, List
from pathlib import Path
import pandas as pd
import httpx

logger = logging.getLogger(__name__)


class GeneMappingService:
    """
    Service for mapping probe IDs to gene symbols using GEO platform annotations
    """
    
    CACHE_DIR = Path("/tmp/gpl_cache")
    MEMORY_CACHE_FILE = CACHE_DIR / ".memory_cache_index.json"
    EMPTY_MAPPING_PLATFORMS_FILE = CACHE_DIR / ".empty_mapping_platforms.json"
    PARTIAL_DOWNLOADS_DIR = CACHE_DIR / ".partial_downloads"
    GEO_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/platforms"
    MAX_RETRIES = 2  # Reduced retries to prevent long delays
    RETRY_BACKOFF = 2.0  # Exponential backoff multiplier
    CHUNK_SIZE = 200 * 1024 * 1024  # 200MB chunks for optimal throughput on large files
    
    def __init__(self):
        """Initialize gene mapping service"""
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.PARTIAL_DOWNLOADS_DIR.mkdir(exist_ok=True)
        # Path to pre-created mapping files from platform loading
        # Go up to backend directory, then to platform_mappings
        self.PREBUILT_PLATFORM_DIR = Path(__file__).parent.parent.parent / "platform_mappings"
        self.PREBUILT_PLATFORM_DIR.mkdir(exist_ok=True)
        # Large timeout for downloading potentially multi-GB platform files
        # Will be overridden per-request with smart timeout calculation
        self.client = httpx.AsyncClient(timeout=1800.0, follow_redirects=True)  # Increased from 600s to 1800s (30 minutes)
        # Cache only platform IDs, not the actual mappings (to save memory)
        self._cached_platform_ids: set = set()
        # Small in-memory cache for recently accessed mappings (LRU-like)
        self._mapping_cache: Dict[str, Dict[str, str]] = {}
        self.MAX_CACHE_SIZE = 3  # Only keep 3 platforms in memory
        # Track known invalid platforms (404 errors) to avoid repeated failed attempts
        self._invalid_platforms: set = set()
        # Track platforms that downloaded successfully but have NO gene mappings
        # These should NOT be retried since the file is valid but has no usable data
        self._empty_mapping_platforms: set = set()
        # Load list of previously cached platforms on init
        self._load_memory_cache_index()
        # Load empty mapping platforms cache (this prevents infinite retry loops)
        self._load_empty_mapping_platforms_cache()
    
    def _load_memory_cache_index(self) -> None:
        """Load index of cached platforms (not the actual data) to track what's cached on disk"""
        try:
            if self.MEMORY_CACHE_FILE.exists():
                with open(self.MEMORY_CACHE_FILE, 'r') as f:
                    cache_index = json.load(f)
                
                # Only track which platforms are cached on disk, don't load them into memory yet
                self._cached_platform_ids = set(cache_index.get('cached_platforms', []))
                logger.debug(f"Index loaded: {len(self._cached_platform_ids)} platforms available on disk")
        except Exception as e:
            logger.debug(f"Could not load memory cache index: {e}")
    
    def _load_empty_mapping_platforms_cache(self) -> None:
        """Load list of platforms that have been downloaded but contain no gene mappings.
        
        These platforms should NOT be retried since:
        1. The file downloads successfully (no 404)
        2. The file parses successfully (valid format)
        3. But there are no probe->gene_symbol mappings in the data
        
        Examples: GPL16791, GPL17021 - methylation arrays with no gene symbols
        """
        try:
            if self.EMPTY_MAPPING_PLATFORMS_FILE.exists():
                with open(self.EMPTY_MAPPING_PLATFORMS_FILE, 'r') as f:
                    cache_data = json.load(f)
                
                self._empty_mapping_platforms = set(cache_data.get('empty_mapping_platforms', []))
                if self._empty_mapping_platforms:
                    logger.info(f"Loaded {len(self._empty_mapping_platforms)} platforms known to have no gene mappings (will skip)")
        except Exception as e:
            logger.debug(f"Could not load empty mapping platforms cache: {e}")
    
    def _save_empty_mapping_platforms_cache(self) -> None:
        """Save list of platforms that have no gene mappings to persistent storage"""
        try:
            cache_data = {
                'empty_mapping_platforms': list(self._empty_mapping_platforms)
            }
            with open(self.EMPTY_MAPPING_PLATFORMS_FILE, 'w') as f:
                json.dump(cache_data, f)
            logger.info(f"Saved empty mapping platforms cache: {len(self._empty_mapping_platforms)} platforms")
        except Exception as e:
            logger.debug(f"Failed to save empty mapping platforms cache: {e}")
    
    def _save_memory_cache_index(self) -> None:
        """Save index of cached platforms to persistent storage"""
        try:
            cache_index = {
                'cached_platforms': list(self._cached_platform_ids)
            }
            with open(self.MEMORY_CACHE_FILE, 'w') as f:
                json.dump(cache_index, f)
            logger.debug(f"Saved memory cache index: {len(self._cached_platform_ids)} platforms")
        except Exception as e:
            logger.debug(f"Failed to save memory cache index: {e}")
    
    def _get_prebuilt_mapping_path(self, platform_id: str) -> Optional[Path]:
        """Check if a pre-built gene mapping file exists for this platform.
        
        Looks for TSV files first (from download_platforms.py), then parquet files.
        Files are in the platform_mappings directory with clean probe->gene mappings.
        
        Args:
            platform_id: Platform ID (e.g., 'GPL23038' or '23038')
            
        Returns:
            Path to the mapping file if it exists, None otherwise
        """
        try:
            # Normalize platform ID to GPL format
            if not platform_id.startswith('GPL'):
                platform_id = f'GPL{platform_id}'
            
            # Look for TSV file first (preferred format from download_platforms.py)
            tsv_path = self.PREBUILT_PLATFORM_DIR / f"{platform_id}_mappings.tsv"
            if tsv_path.exists() and tsv_path.stat().st_size > 0:
                logger.info(f"Found pre-built TSV for {platform_id} at {tsv_path}")
                return tsv_path
            
            # Fallback to parquet
            parquet_path = self.PREBUILT_PLATFORM_DIR / f"{platform_id}_gene_mapping.parquet"
            if parquet_path.exists() and parquet_path.stat().st_size > 0:
                logger.info(f"Found pre-built parquet for {platform_id} at {parquet_path}")
                return parquet_path
        except Exception as e:
            logger.warning(f"Error checking for pre-built mappings for {platform_id}: {e}")
        
        return None

    def _load_from_prebuilt_file(self, platform_id: str, file_path: Path) -> Dict[str, str]:
        """Load gene mappings from a pre-built file (TSV or parquet).
        
        Args:
            platform_id: Platform ID
            file_path: Path to the mapping file
            
        Returns:
            Dictionary mapping probe IDs to gene symbols
        """
        try:
            logger.info(f"Loading {platform_id} from pre-built file: {file_path}")
            
            # Handle TSV files
            if file_path.suffix == '.tsv':
                mapping = {}
                with open(file_path, 'r') as f:
                    # Skip header
                    header = f.readline().strip().split('\t')
                    
                    # Find column indices
                    probe_col = None
                    gene_col = None
                    for i, col in enumerate(header):
                        col_lower = col.lower()
                        if col_lower in ['probe_id', 'id', 'probeset_id', 'probe']:
                            probe_col = i
                        elif col_lower in ['gene_symbol', 'symbol', 'gene', 'gene_name']:
                            gene_col = i
                    
                    if probe_col is None or gene_col is None:
                        logger.error(f"Could not find required columns in {file_path}. Header: {header}")
                        return {}
                    
                    # Read mappings
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) > max(probe_col, gene_col):
                            probe_id = parts[probe_col].strip()
                            gene_symbol = parts[gene_col].strip()
                            
                            # Skip invalid entries
                            if probe_id and gene_symbol and gene_symbol.lower() not in ['', 'na', 'null', 'n/a']:
                                mapping[probe_id] = gene_symbol
                
                logger.info(f"Loaded {len(mapping)} probe->gene mappings from TSV for {platform_id}")
                return mapping
            
            # Handle parquet files
            elif file_path.suffix == '.parquet':
                import pandas as pd
                
                df = pd.read_parquet(file_path)
                
                # Create mapping from ID -> gene_symbol
                mapping = {}
                # Try different column name combinations (case-insensitive)
                id_cols = ['probe_id', 'ID', 'id', 'probeset_id']
                symbol_cols = ['gene_symbol', 'symbol', 'gene', 'gene_name', 'GENE_SYMBOL', 'SYMBOL', 'GENE', 'GENE_NAME']
                
                id_col = None
                symbol_col = None
                
                # Find ID column (case-insensitive)
                for col in df.columns:
                    col_upper = col.upper()
                    if col_upper in [c.upper() for c in id_cols]:
                        id_col = col
                        break
                
                # Find gene symbol column (case-insensitive, prioritize GENE_SYMBOL)
                for col in df.columns:
                    col_upper = col.upper()
                    if col_upper == 'GENE_SYMBOL':
                        symbol_col = col
                        break
                
                # If GENE_SYMBOL not found, try other variations
                if not symbol_col:
                    for col in df.columns:
                        col_upper = col.upper()
                        if col_upper in [c.upper() for c in symbol_cols]:
                            symbol_col = col
                            break
                
                if id_col and symbol_col:
                    for idx, row in df.iterrows():
                        probe_id = str(row[id_col]).strip()
                        gene_symbol = str(row[symbol_col]).strip() if pd.notna(row[symbol_col]) else None
                        if probe_id and gene_symbol and gene_symbol != "nan" and gene_symbol:
                            mapping[probe_id] = gene_symbol
                
                logger.info(f"Loaded {len(mapping)} probe->gene mappings from parquet for {platform_id}")
                return mapping
            
            else:
                logger.error(f"Unsupported file format: {file_path.suffix}")
                return {}
            
        except Exception as e:
            logger.error(f"Failed to load pre-built file for {platform_id}: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def get_batch_probe_to_gene_mappings(
        self,
        platform_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, Optional[Dict[str, str]]]:
        """
        Get mappings for multiple platforms in parallel (much faster than sequential calls).
        Limited to 4 concurrent downloads to avoid resource exhaustion.
        
        Args:
            platform_ids: List of GEO platform IDs
            use_cache: Whether to use cached mappings
        
        Returns:
            Dictionary mapping platform_id -> mapping (or None if failed)
        """
        logger.info(f"Fetching mappings for {len(platform_ids)} platforms (max 4 concurrent)")
        
        # Limit concurrent downloads to 4 to avoid resource exhaustion
        semaphore = asyncio.Semaphore(4)
        
        async def fetch_with_limit(pid: str) -> tuple:
            async with semaphore:
                result = await self.get_probe_to_gene_mapping(pid, use_cache)
                return pid, result
        
        # Use asyncio.gather with limited concurrency
        results = await asyncio.gather(
            *[fetch_with_limit(pid) for pid in platform_ids],
            return_exceptions=False
        )
        
        # Return as dict mapping platform_id to result
        mappings = {pid: result for pid, result in results}
        successful = sum(1 for m in mappings.values() if m is not None)
        logger.info(f"Successfully loaded {successful}/{len(platform_ids)} platform mappings")
        
        return mappings
    
    async def get_probe_to_gene_mapping(
        self,
        platform_id: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, str]]:
        """
        Get mapping from probe IDs to gene symbols for a platform.
        Loads from disk on-demand to minimize memory footprint.
        
        Args:
            platform_id: GEO platform ID (e.g., "GPL1261")
            use_cache: Whether to use cached mapping
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if failed
        """
        # Normalize platform ID first for consistent cache keys
        normalized_id = platform_id if platform_id.startswith('GPL') else f'GPL{platform_id}'

        # Check small in-memory cache first
        if normalized_id in self._mapping_cache:
            logger.debug(f"Using in-memory cache for {normalized_id}")
            return self._mapping_cache[normalized_id]
        
        # Check if this platform is known to have no gene mappings (skip download entirely)
        if normalized_id in self._empty_mapping_platforms or platform_id in self._empty_mapping_platforms:
            logger.warning(f"Platform {platform_id} is known to have no gene mappings (methylation/other array), skipping")
            return None
        
        # Check for pre-built mapping files first (TSV or parquet from download_platforms.py)
        prebuilt_path = self._get_prebuilt_mapping_path(platform_id)
        if prebuilt_path:
            try:
                mapping = self._load_from_prebuilt_file(platform_id, prebuilt_path)
                
                if mapping:
                    # Only keep small mappings in memory cache (< 100k entries)
                    if len(mapping) < 100000:
                        self._mapping_cache[normalized_id] = mapping
                        # Enforce max cache size - remove oldest if over limit
                        if len(self._mapping_cache) > self.MAX_CACHE_SIZE:
                            oldest = next(iter(self._mapping_cache))
                            del self._mapping_cache[oldest]
                            logger.debug(f"Evicted {oldest} from memory cache (size limit reached)")
                    
                    return mapping
                else:
                    logger.warning(f"Pre-built file for {platform_id} exists but is empty")
            except Exception as e:
                logger.warning(f"Failed to load pre-built file for {platform_id}: {e}")
                # Fall through to try disk cache and then download
        
        # This block is now redundant since we check for pre-built files above
        # Kept for backwards compatibility with old parquet files
        mapping_path = self.PREBUILT_PLATFORM_DIR / f"{normalized_id}_gene_mapping.parquet"
        if use_cache and mapping_path.exists():
            try:
                mapping_df = pd.read_parquet(mapping_path)
                
                # Try different column names
                id_col = 'probe_id' if 'probe_id' in mapping_df.columns else 'ID'
                symbol_col = 'gene_symbol' if 'gene_symbol' in mapping_df.columns else 'symbol'
                
                if id_col in mapping_df.columns and symbol_col in mapping_df.columns:
                    mapping = dict(zip(mapping_df[id_col], mapping_df[symbol_col]))
                    
                    # Only keep small mappings in memory cache (< 100k entries)
                    if len(mapping) < 100000:
                        self._mapping_cache[normalized_id] = mapping
                        # Enforce max cache size - remove oldest if over limit
                        if len(self._mapping_cache) > self.MAX_CACHE_SIZE:
                            oldest = next(iter(self._mapping_cache))
                            del self._mapping_cache[oldest]
                            logger.debug(f"Evicted {oldest} from memory cache (size limit reached)")
                    
                    logger.info(f"Loaded mapping for {platform_id} from platform_mappings: {len(mapping)} probes")
                    return mapping
            except Exception as e:
                logger.warning(f"Failed to load mapping for {platform_id}: {e}")
                pass
        
        # Fetch from GEO with timeout protection
        try:
            mapping = await asyncio.wait_for(
                self._fetch_platform_mapping(platform_id),
                timeout=18000  # 5 hour timeout per platform (allows download of multi-GB files)
            )
        except asyncio.TimeoutError:
            logger.error(f"Platform mapping download timed out for {platform_id}")
            return None
        
        if mapping:
            # Only keep small mappings in memory
            if len(mapping) < 100000:
                self._mapping_cache[normalized_id] = mapping
                # Enforce max cache size
                if len(self._mapping_cache) > self.MAX_CACHE_SIZE:
                    oldest = next(iter(self._mapping_cache))
                    del self._mapping_cache[oldest]
                    logger.debug(f"Evicted {oldest} from memory cache (size limit reached)")
            
            # Save to disk cache
            if use_cache:
                try:
                    await self._save_mapping_to_parquet(normalized_id, mapping)
                except Exception as e:
                    logger.warning(f"Failed to save cache for {platform_id}: {e}")
        
        return mapping
    
    async def _save_mapping_to_parquet(self, platform_id: str, mapping: Dict[str, str]) -> None:
        """
        Save mapping to parquet file in platform_mappings directory
        
        Args:
            platform_id: Platform ID
            mapping: Probe ID to gene symbol mapping
        """
        mapping_path = self.PREBUILT_PLATFORM_DIR / f"{platform_id}_gene_mapping.parquet"
        
        # Convert to DataFrame and save with compression
        mapping_df = pd.DataFrame([
            {'probe_id': k, 'gene_symbol': v}
            for k, v in mapping.items()
        ])
        
        # Save with snappy compression for better performance
        mapping_df.to_parquet(mapping_path, compression='snappy', index=False)
        
        # Track this platform as cached
        self._cached_platform_ids.add(platform_id)
        self._save_memory_cache_index()
        
        logger.info(f"Saved mapping for {platform_id} to platform_mappings: {len(mapping)} probes, {mapping_path.stat().st_size / (1024*1024):.1f}MB")
    
    async def _fetch_platform_mapping(self, platform_id: str) -> Optional[Dict[str, str]]:
        """
        Fetch platform mapping from GEO with retry logic and folder prefix calculation
        
        Args:
            platform_id: Platform ID (e.g., "GPL1261" or "1261" or "13912")
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if failed
        """
        logger.info(f"Fetching platform mapping for {platform_id}")
        
        # Check if this platform is known to be invalid
        if platform_id in self._invalid_platforms:
            logger.warning(f"Platform {platform_id} is known to be invalid (404), skipping")
            return None
        
        # Normalize platform_id to GPL format
        if platform_id.startswith("GPL"):
            gpl_id = platform_id
            numeric_id = platform_id[3:]  # Remove "GPL" prefix
        else:
            numeric_id = platform_id
            gpl_id = f"GPL{platform_id}"
        
        # Construct folder prefix for GEO FTP location
        # GEO FTP structure: /geo/platforms/GPLnnn/GPLXXXX/soft/
        # Examples:
        # - GPL1261 -> /geo/platforms/GPL1nnn/GPL1261/soft/GPL1261_family.soft.gz
        # - GPL13912 -> /geo/platforms/GPL13nnn/GPL13912/soft/GPL13912_family.soft.gz
        # - GPL570 -> /geo/platforms/GPLnnn/GPL570/soft/GPL570_family.soft.gz
        # - GPL96 -> /geo/platforms/GPLnnn/GPL96/soft/GPL96_family.soft.gz
        # Pattern: Platforms with ID < 1000 go to GPLnnn, otherwise remove last 3 digits and append "nnn"
        
        numeric_value = int(numeric_id)
        if numeric_value < 1000:
            # All platforms with IDs < 1000 (1-999) are in GPLnnn folder
            folder_prefix = "GPLnnn"
        else:
            # Standard case: 4 or more digits (e.g., 1261, 13912, 6246)
            # Remove last 3 digits and append "nnn"
            folder_prefix = f"GPL{numeric_id[:-3]}nnn"
        
        logger.debug(f"Calculated folder prefix for {gpl_id}: {folder_prefix}")
        
        # Try with minimal retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                mapping = await self._fetch_with_retry(gpl_id, folder_prefix)
                if mapping:
                    return mapping
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed for {gpl_id}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = (self.RETRY_BACKOFF ** attempt)
                    logger.debug(f"Retrying {gpl_id} in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
        
        # NOTE: Disabled persistent invalid marking to allow retries in new sessions
        # Only mark as invalid in-memory for this session
        # self._invalid_platforms.add(platform_id)
        # self._save_invalid_platforms_cache()
        
        logger.warning(f"Failed to fetch mapping for {gpl_id} after {self.MAX_RETRIES} retries")
        return None
    
    async def _download_with_chunks_and_resume(self, url: str, gpl_id: str) -> Optional[bytes]:
        """
        Download file with chunked streaming and resume capability.
        Validates Content-Length before and after download.
        
        Args:
            url: URL to download
            gpl_id: GPL ID for cache file naming
        
        Returns:
            File content as bytes, or None if download failed
        """
        partial_file = self.PARTIAL_DOWNLOADS_DIR / f"{gpl_id}.partial"
        content_file = self.PARTIAL_DOWNLOADS_DIR / f"{gpl_id}.content_length"
        
        try:
            # Get file size via HEAD request
            try:
                head_response = await self.client.head(url, timeout=60.0)
                if head_response.status_code != 200:
                    logger.debug(f"HEAD request failed for {gpl_id}: {head_response.status_code}")
                    return None
                
                expected_size = int(head_response.headers.get('content-length', 0))
                if expected_size <= 0:
                    logger.debug(f"No valid Content-Length for {gpl_id}")
                    return None
                
                # Store expected size for validation
                with open(content_file, 'w') as f:
                    f.write(str(expected_size))
                
                file_size_mb = expected_size / (1024 * 1024)
                logger.debug(f"Starting download for {gpl_id}: {file_size_mb:.1f}MB")
                
            except Exception as e:
                logger.debug(f"Could not determine file size for {gpl_id}: {e}")
                return None
            
            # Calculate timeout based on file size
            # Conservative estimate: 5-10 MB/sec (accounting for network variability)
            base_timeout = (expected_size / (1024 * 1024)) / 5.0
            timeout_seconds = base_timeout * 2.0 + 120.0  # 2x multiplier + 2 min buffer
            timeout_seconds = min(timeout_seconds, 1800.0)  # Cap at 30 minutes
            
            http_timeout = httpx.Timeout(timeout=timeout_seconds, connect=30.0, read=300.0)
            
            # Check if we have a partial download to resume
            resume_header = {}
            bytes_downloaded = 0
            if partial_file.exists():
                bytes_downloaded = partial_file.stat().st_size
                if bytes_downloaded < expected_size:
                    logger.debug(f"Resuming download for {gpl_id}: {bytes_downloaded}/{expected_size} bytes")
                    resume_header = {'Range': f'bytes={bytes_downloaded}-'}
                else:
                    # Partial file is complete, remove it
                    partial_file.unlink()
                    bytes_downloaded = 0
            
            # Download with chunked streaming
            downloaded_data = bytearray()
            async with self.client.stream('GET', url, timeout=http_timeout, headers=resume_header) as response:
                if response.status_code not in [200, 206]:  # 206 = Partial Content (resume)
                    logger.debug(f"Download failed with status {response.status_code} for {gpl_id}")
                    return None
                
                # For resumed downloads, validate Content-Range
                if resume_header and 'content-range' in response.headers:
                    logger.debug(f"Resumed download for {gpl_id}: {response.headers['content-range']}")
                
                # Stream download in chunks
                async for chunk in response.aiter_bytes(chunk_size=self.CHUNK_SIZE):
                    downloaded_data.extend(chunk)
                    bytes_downloaded += len(chunk)
                    
                    # Log progress for large files
                    if expected_size > 100 * 1024 * 1024:  # Only log for files > 100MB
                        progress_pct = (bytes_downloaded / expected_size) * 100
                        if bytes_downloaded % (10 * 1024 * 1024) == 0:  # Log every 10MB
                            logger.debug(f"{gpl_id} download progress: {progress_pct:.1f}%")
            
            # Validate Content-Length after download
            actual_size = len(downloaded_data)
            if actual_size != expected_size:
                logger.warning(f"Content-Length mismatch for {gpl_id}: expected {expected_size}, got {actual_size}")
                # Try to save partial data in case we want to resume
                if actual_size > 0:
                    with open(partial_file, 'wb') as f:
                        f.write(downloaded_data)
                return None
            
            logger.info(f"Successfully downloaded {gpl_id}: {actual_size / (1024*1024):.1f}MB")
            
            # Clean up partial file if it exists (download completed)
            if partial_file.exists():
                partial_file.unlink()
            if content_file.exists():
                content_file.unlink()
            
            return bytes(downloaded_data)
            
        except asyncio.TimeoutError:
            logger.error(f"Download timeout for {gpl_id} from {url}")
            # Save what we have so far for resume
            if len(downloaded_data) > 0:
                with open(partial_file, 'wb') as f:
                    f.write(downloaded_data)
            return None
        except Exception as e:
            logger.error(f"Download error for {gpl_id}: {e}")
            return None
    
    async def _fetch_with_retry(self, gpl_id: str, folder_prefix: str) -> Optional[Dict[str, str]]:
        """
        Attempt to fetch platform mapping, trying annotation file first (small), 
        then family format as fallback.
        Uses chunked downloads with resume capability and Content-Length validation.
        
        Args:
            gpl_id: GPL ID
            folder_prefix: Folder prefix for FTP path
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if all formats fail
        """
        # Track if we successfully downloaded but got no mappings (vs download failure)
        downloaded_successfully = False
        
        # Try annotation file first (much smaller, typically 1-10MB vs 1-70GB for family files)
        annot_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/annot/{gpl_id}.annot.gz"
        try:
            logger.debug(f"Trying annotation file first for {gpl_id}...")
            annot_result = await self._try_annotation_file(gpl_id, annot_url)
            if annot_result:
                logger.info(f"Successfully loaded {gpl_id} from annotation file: {len(annot_result)} probes")
                return annot_result
        except Exception as e:
            logger.debug(f"Annotation file not available for {gpl_id}: {e}")
        
        # Try family format (can be very large - 1MB to 70GB+)
        family_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/soft/{gpl_id}_family.soft.gz"
        
        retry_count = 0
        while retry_count < self.MAX_RETRIES:
            try:
                logger.debug(f"Attempting to download {gpl_id} (attempt {retry_count + 1}/{self.MAX_RETRIES})")
                
                # Download with chunked streaming and resume
                file_data = await self._download_with_chunks_and_resume(family_url, gpl_id)
                
                if file_data:
                    downloaded_successfully = True
                    # Decompress and parse with streaming to minimize memory
                    try:
                        logger.debug(f"Decompressing and parsing {gpl_id}...")
                        mapping = self._parse_gpl_file_streaming(file_data, gpl_id)
                        
                        if mapping:
                            logger.info(f"Successfully fetched mapping for {gpl_id}: {len(mapping)} probes")
                            return mapping
                        else:
                            # File parsed but no mappings found - this platform has no gene symbols
                            # Cache this so we don't retry (e.g., methylation arrays)
                            logger.warning(f"Platform {gpl_id} downloaded and parsed but has NO gene mappings - caching to skip future attempts")
                            self._empty_mapping_platforms.add(gpl_id)
                            self._save_empty_mapping_platforms_cache()
                            return None
                    except Exception as e:
                        logger.debug(f"Error decompressing/parsing {gpl_id}: {e}")
                        retry_count += 1
                        if retry_count < self.MAX_RETRIES:
                            wait_time = 2 ** retry_count  # Exponential backoff
                            logger.debug(f"Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        continue
                else:
                    # Download failed, retry with backoff
                    retry_count += 1
                    if retry_count < self.MAX_RETRIES:
                        wait_time = 2 ** retry_count  # Exponential backoff
                        logger.debug(f"Download failed, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    continue
                    
            except Exception as e:
                logger.debug(f"Error fetching family format for {gpl_id}: {e}")
                retry_count += 1
                if retry_count < self.MAX_RETRIES:
                    wait_time = 2 ** retry_count
                    logger.debug(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        # Try miniml format as fallback (only if family format failed)
        if not downloaded_successfully:
            logger.debug(f"Family format failed, trying miniml format for {gpl_id}...")
            miniml_result = await self._try_miniml_format(gpl_id, folder_prefix)
            if miniml_result:
                return miniml_result
        
        return None
    
    async def _try_annotation_file(self, gpl_id: str, annot_url: str) -> Optional[Dict[str, str]]:
        """
        Try to download and parse the annotation file (much smaller than family files).
        Annotation files are typically 1-10MB vs family files which can be 1-70GB+.
        
        Args:
            gpl_id: Platform ID
            annot_url: URL to annotation file
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if failed
        """
        try:
            # Check if file exists first
            head_response = await self.client.head(annot_url, follow_redirects=True)
            if head_response.status_code != 200:
                logger.debug(f"Annotation file not found for {gpl_id}")
                return None
            
            file_size = int(head_response.headers.get('content-length', 0))
            if file_size == 0:
                logger.debug(f"Annotation file empty for {gpl_id}")
                return None
            
            logger.info(f"Downloading annotation file for {gpl_id}: {file_size / (1024*1024):.1f}MB")
            
            # Download the annotation file
            response = await self.client.get(annot_url, follow_redirects=True, timeout=300.0)
            if response.status_code != 200:
                return None
            
            # Parse the annotation file
            return self._parse_annotation_file(response.content, gpl_id)
            
        except Exception as e:
            logger.debug(f"Error downloading annotation file for {gpl_id}: {e}")
            return None
    
    def _parse_annotation_file(self, compressed_data: bytes, platform_id: str) -> Optional[Dict[str, str]]:
        """
        Parse GPL annotation file (tab-separated with headers).
        Format is similar to family files but much smaller and focused on annotations.
        
        Args:
            compressed_data: Gzipped compressed file data
            platform_id: Platform ID for logging
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol
        """
        import gzip
        import io
        
        try:
            # Decompress
            decompressed = gzip.decompress(compressed_data)
            text_stream = io.StringIO(decompressed.decode('utf-8', errors='replace'))
            
            mapping = {}
            headers = None
            id_idx = None
            symbol_idx = None
            in_table = False
            
            for line in text_stream:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Look for the start of the data table
                if line == '!platform_table_begin':
                    in_table = True
                    continue
                elif line == '!platform_table_end':
                    break
                
                # Skip metadata lines (before table starts)
                if not in_table:
                    continue
                
                parts = line.split('\t')
                
                # First line in table is the header
                if headers is None:
                    headers = parts
                    
                    # Find ID and Gene Symbol columns
                    for idx, header in enumerate(headers):
                        header_upper = header.upper().strip()
                        
                        # Look for ID column
                        if header_upper in ['ID', 'PROBE_ID', 'ID_REF', 'PROBESET_ID']:
                            id_idx = idx
                        # Look for Gene Symbol column (exclude GENE_ID which contains numeric Entrez IDs)
                        elif header_upper in ['GENE SYMBOL', 'GENE_SYMBOL', 'SYMBOL', 'GENE_NAME', 
                                               'GENE ASSIGNMENT', 'GENE_ASSIGNMENT']:
                            # Make sure it's not GENE_ID column
                            if 'GENE_ID' not in header_upper and 'GENEID' not in header_upper:
                                symbol_idx = idx
                    
                    # Fallback: look for columns containing 'gene' and 'symbol'
                    if symbol_idx is None:
                        for idx, header in enumerate(headers):
                            header_upper = header.upper()
                            if 'GENE' in header_upper and 'SYMBOL' in header_upper:
                                symbol_idx = idx
                                break
                    
                    # Try 'gene' column as last resort
                    if symbol_idx is None:
                        for idx, header in enumerate(headers):
                            if header.upper() == 'GENE':
                                symbol_idx = idx
                                break
                    
                    logger.debug(f"Annotation file headers for {platform_id}: ID col={id_idx}, Symbol col={symbol_idx}")
                    if id_idx is None or symbol_idx is None:
                        logger.warning(f"Could not find required columns in annotation file for {platform_id}. Headers: {headers[:15]}")
                        return None
                    continue
                
                # Parse data row
                if id_idx is not None and len(parts) > id_idx:
                    probe_id = parts[id_idx].strip()
                    
                    if not probe_id:
                        continue
                    
                    gene_symbol = None
                    if symbol_idx is not None and len(parts) > symbol_idx:
                        gene_symbol = parts[symbol_idx].strip()
                    
                    # Handle multiple genes separated by ///
                    if gene_symbol and '///' in gene_symbol:
                        gene_symbol = gene_symbol.split('///')[0].strip()
                    
                    # Also handle // separator sometimes used
                    if gene_symbol and ' // ' in gene_symbol:
                        gene_symbol = gene_symbol.split(' // ')[0].strip()
                    
                    if gene_symbol and gene_symbol.lower() not in ['', 'null', 'na', 'n/a', '---']:
                        mapping[probe_id] = gene_symbol
            
            if mapping:
                logger.info(f"Parsed annotation file for {platform_id}: {len(mapping)} probes")
                return mapping
            else:
                logger.debug(f"No mappings found in annotation file for {platform_id}")
                return None
                
        except Exception as e:
            logger.debug(f"Error parsing annotation file for {platform_id}: {e}")
            return None

    def _parse_gpl_file_streaming(self, compressed_data: bytes, platform_id: str) -> Optional[Dict[str, str]]:
        """
        Parse GPL family file with streaming decompression to minimize memory usage.
        Processes file line-by-line without loading entire decompressed content into memory.
        
        Args:
            compressed_data: Gzipped compressed file data
            platform_id: Platform ID for logging
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol
        """
        try:
            mapping = {}
            lines_processed = 0
            table_started = False
            in_table_section = False  # Track if we've passed !platform_table_begin
            id_idx = None
            symbol_idx = None
            
            # Use gzip stream reader for chunked decompression
            with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as gz:
                for line_bytes in gz:
                    line = line_bytes.decode('utf-8', errors='ignore').rstrip('\n')
                    lines_processed += 1
                    
                    # Skip empty lines and comment-only lines
                    if not line or line.startswith('#!') or line.startswith('##'):
                        continue
                    
                    # Check for platform_table_begin marker
                    if '!platform_table_begin' in line.lower():
                        in_table_section = True
                        continue

                    # CRITICAL: Stop at platform_table_end or when entering SAMPLE section
                    # This prevents parsing sample expression data as gene symbols
                    if '!platform_table_end' in line.lower() or line.startswith('^SAMPLE'):
                        if mapping:
                            logger.debug(f"{platform_id}: Stopped at platform table end with {len(mapping)} mappings")
                        break

                    # Skip column description lines (e.g., "#ID = Description text")
                    # These are single-column descriptions, not the actual header
                    if line.startswith('#') and '=' in line and '\t' not in line:
                        continue
                    
                    # Find table header line - can start with #ID OR be first line after !platform_table_begin
                    if not table_started and (line.startswith('#ID') or (in_table_section and (line.startswith('ID') or line.upper().startswith('ID')))):
                        table_started = True
                        headers = line.split('\t')
                        
                        logger.debug(f"Found header at line {lines_processed}: {[h.lstrip('#') for h in headers[:10]]}")
                        
                        # First pass: look for exact matches
                        # Clean headers by removing #, =, and extra spaces
                        for idx, header in enumerate(headers):
                            # Remove # prefix and any " = " suffix pattern (e.g., "#ID = " -> "ID")
                            header_clean = header.lstrip('#').split('=')[0].strip().upper()
                            
                            if header_clean in ['ID', 'ID_REF', 'PROBE_ID', 'SEQUENCE_ACCESSION']:
                                id_idx = idx
                            # Prioritize GENE_SYMBOL over GENE_ID (numeric Entrez IDs)
                            # Include "GENE SYMBOL" (with space) for platforms like GPL16043
                            elif header_clean in ['GENE_SYMBOL', 'GENE SYMBOL', 'SYMBOL', 'GENE_NAME', 'ORF', 'GENE']:
                                # Make sure it's not GENE_ID column (we want symbols, not numeric IDs)
                                if 'GENE_ID' not in header_clean and 'GENEID' not in header_clean:
                                    symbol_idx = idx
                        
                        # Second pass: flexible matching for ID column
                        if id_idx is None:
                            for idx, header in enumerate(headers):
                                header_clean = header.lstrip('#').split('=')[0].strip().upper()
                                if any(x in header_clean for x in ['ID', 'ACCESSION', 'PROBE']):
                                    id_idx = idx
                                    break
                        
                        # Third pass: flexible matching for gene symbol column
                        if symbol_idx is None:
                            for idx, header in enumerate(headers):
                                header_clean = header.lstrip('#').split('=')[0].strip().upper()
                                # Exclude GENE_ID - we want gene symbols, not numeric Entrez IDs
                                if 'GENE_ID' not in header_clean and 'GENEID' not in header_clean:
                                    if any(x in header_clean for x in ['GENE_SYMBOL', 'GENE_NAME', 'SYMBOL', 
                                                                         'ORF', 'GENE', 'DESCRIPTION', 'PRODUCT']):
                                        symbol_idx = idx
                                        break
                        
                        # Fourth pass: use common aliases
                        if symbol_idx is None:
                            for idx, header in enumerate(headers):
                                header_clean = header.lstrip('#').split('=')[0].strip().upper()
                                if any(x == header_clean for x in ['NAME', 'TITLE', 'DEFINITION']):
                                    symbol_idx = idx
                                    break
                        
                        logger.debug(f"Detected columns - ID: {id_idx} ({headers[id_idx] if id_idx is not None else 'NOT FOUND'}), "
                                   f"Symbol: {symbol_idx} ({headers[symbol_idx] if symbol_idx is not None else 'NOT FOUND'})")
                        continue
                    
                    # Skip lines before table starts or comment lines
                    if not table_started or line.startswith('#'):
                        continue
                    
                    # Parse data rows
                    parts = line.split('\t')
                    if id_idx is None or len(parts) <= id_idx:
                        continue
                    
                    probe_id = parts[id_idx].strip()
                    
                    # Skip empty or invalid probe IDs
                    if not probe_id or probe_id.startswith('#'):
                        continue
                    
                    # Extract gene symbol
                    gene_symbol = None
                    if symbol_idx is not None and len(parts) > symbol_idx:
                        gene_symbol = parts[symbol_idx].strip()
                    
                    # Use first gene if multiple are listed (separated by ///)
                    if gene_symbol and '///' in gene_symbol:
                        gene_symbol = gene_symbol.split('///')[0].strip()
                    
                    # Skip if no valid gene symbol
                    if not gene_symbol or gene_symbol == '' or gene_symbol.lower() in ['null', 'na', 'n/a']:
                        continue
                    
                    mapping[probe_id] = gene_symbol
                    
                    # Log progress every 100k lines
                    if lines_processed % 100000 == 0:
                        logger.debug(f"{platform_id}: Processed {lines_processed} lines, found {len(mapping)} mappings")
            
            if mapping:
                logger.info(f"Parsed GPL file for {platform_id}: {len(mapping)} probes from {lines_processed} lines")
            else:
                logger.warning(f"No valid mappings found in GPL file for {platform_id} ({lines_processed} lines processed)")
            
            return mapping if mapping else None
        
        except Exception as e:
            logger.error(f"Error parsing GPL file (streaming) for {platform_id}: {e}")
            return None
    
    async def _try_miniml_format(self, gpl_id: str, folder_prefix: str) -> Optional[Dict[str, str]]:
        """
        Try alternative miniml format for platform data.
        Miniml format is XML-based and provides structured gene annotation data.
        
        Args:
            gpl_id: Platform ID in GPL format
            folder_prefix: Folder prefix (e.g., "GPL13nnn" for GPL13912)
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if failed
        """
        try:
            # Try miniml directory structure
            miniml_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/miniml"
            logger.debug(f"Trying miniml format for {gpl_id} at: {miniml_url}")
            
            # Check if miniml directory exists
            response = await self.client.get(miniml_url)
            if response.status_code != 200:
                logger.debug(f"Miniml directory not available for {gpl_id}")
                return None
            
            # Parse HTML directory listing to find XML file
            import re
            html_content = response.text
            
            # Look for .xml.gz file in directory listing
            xml_files = re.findall(r'href=["\']([^"\']*\.xml\.gz)["\']', html_content)
            
            if not xml_files:
                logger.debug(f"No XML files found in miniml directory for {gpl_id}")
                return None
            
            # Use the first XML file found
            xml_filename = xml_files[0].strip('/')
            xml_url = f"{miniml_url}/{xml_filename}"
            
            logger.info(f"Found miniml XML file for {gpl_id}: {xml_filename}")
            
            # Download and decompress XML
            xml_response = await self.client.get(xml_url)
            if xml_response.status_code != 200:
                logger.debug(f"Failed to download miniml XML for {gpl_id}")
                return None
            
            # Decompress
            xml_content = gzip.decompress(xml_response.content).decode('utf-8', errors='ignore')
            
            # Parse XML for gene mappings
            return self._parse_miniml_xml(xml_content, gpl_id)
            
        except Exception as e:
            logger.debug(f"Error trying miniml format for {gpl_id}: {e}")
            return None
    
    def _parse_miniml_xml(self, xml_content: str, platform_id: str) -> Optional[Dict[str, str]]:
        """
        Parse miniml XML format to extract probe ID -> gene symbol mappings.
        Miniml XML typically contains Platform-Features with sequences and annotations.
        
        Args:
            xml_content: XML content from miniml file
            platform_id: Platform ID for logging
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if parsing fails
        """
        try:
            import xml.etree.ElementTree as ET
            
            logger.debug(f"Parsing miniml XML for {platform_id}")
            
            mapping = {}
            root = ET.fromstring(xml_content)
            
            # Remove namespace to simplify parsing
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            
            # Find all Feature elements (contains probe info)
            # Typical structure: Platform -> PlatformData -> Features -> Feature
            features = root.findall('.//Feature')
            
            if not features:
                logger.debug(f"No Feature elements found in miniml XML for {platform_id}")
                return None
            
            logger.info(f"Found {len(features)} features in miniml XML for {platform_id}")
            
            for feature in features:
                try:
                    # Extract probe ID (usually 'accession' attribute)
                    probe_id = feature.get('accession')
                    if not probe_id:
                        # Try alternative: ID element
                        id_elem = feature.find('ID')
                        probe_id = id_elem.text if id_elem is not None else None
                    
                    if not probe_id:
                        continue
                    
                    # Extract gene information
                    gene_symbol = None
                    
                    # Try to find gene symbol in various locations
                    gene_elem = feature.find('.//Gene')
                    if gene_elem is not None:
                        symbol_elem = gene_elem.find('Symbol')
                        if symbol_elem is not None and symbol_elem.text:
                            gene_symbol = symbol_elem.text.strip()
                    
                    # Fallback: look for annotation with gene info
                    if not gene_symbol:
                        organism_assoc = feature.find('.//OrganismAssociation')
                        if organism_assoc is not None:
                            for annot in organism_assoc.findall('Annotation'):
                                tag = annot.get('tag')
                                if tag and any(x in tag.upper() for x in ['GENE', 'SYMBOL', 'NAME']):
                                    gene_symbol = annot.text
                                    if gene_symbol:
                                        break
                    
                    # Use first gene if multiple are listed
                    if gene_symbol and '///' in gene_symbol:
                        gene_symbol = gene_symbol.split('///')[0].strip()
                    
                    # Add valid mapping
                    if probe_id and gene_symbol and gene_symbol.lower() not in ['null', 'na', '']:
                        mapping[probe_id] = gene_symbol
                
                except (AttributeError, TypeError):
                    continue
            
            if mapping:
                logger.info(f"Parsed miniml XML for {platform_id}: {len(mapping)} probes")
                return mapping
            else:
                logger.debug(f"No valid mappings found in miniml XML for {platform_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error parsing miniml XML for {platform_id}: {e}")
            return None
    
    def map_probes_to_genes(
        self,
        probe_ids: list,
        mapping: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Map a list of probe IDs to gene symbols
        
        Args:
            probe_ids: List of probe IDs
            mapping: Probe ID to gene symbol mapping dictionary
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol (only includes successful mappings)
        """
        result = {}
        unmapped_count = 0
        
        for probe_id in probe_ids:
            if probe_id in mapping:
                result[probe_id] = mapping[probe_id]
            else:
                unmapped_count += 1
        
        if unmapped_count > 0:
            logger.debug(f"Could not map {unmapped_count}/{len(probe_ids)} probes to gene symbols")
        
        return result
    
    def create_gene_symbol_index(
        self,
        probe_mapping: Dict[str, str]
    ) -> Dict[str, list]:
        """
        Create index from gene symbol back to all probe IDs that map to it
        
        Args:
            probe_mapping: Probe ID to gene symbol mapping
        
        Returns:
            Dictionary mapping gene_symbol -> [probe_ids]
        """
        symbol_index = {}
        
        for probe_id, symbol in probe_mapping.items():
            if symbol not in symbol_index:
                symbol_index[symbol] = []
            symbol_index[symbol].append(probe_id)
        
        return symbol_index
    
    async def get_platform_size_mb(self, platform_id: str) -> Optional[float]:
        """
        Get the size of a platform file in MB by checking GEO FTP
        
        Args:
            platform_id: Platform ID (e.g., "GPL1261" or "1261")
        
        Returns:
            Size in MB, or None if unable to determine
        """
        try:
            # Normalize platform_id to GPL format
            if platform_id.startswith("GPL"):
                gpl_id = platform_id
                numeric_id = platform_id[3:]
            else:
                numeric_id = platform_id
                gpl_id = f"GPL{platform_id}"
            
            # Calculate folder prefix (same logic as _fetch_platform_mapping)
            numeric_value = int(numeric_id)
            if numeric_value < 1000:
                folder_prefix = "GPLnnn"
            else:
                folder_prefix = f"GPL{numeric_id[:-3]}nnn"
            
            # If we have a pre-built mapping, report a small size (no download needed)
            prebuilt_path = self._get_prebuilt_mapping_path(gpl_id)
            if prebuilt_path:
                size_mb = prebuilt_path.stat().st_size / (1024 * 1024)
                logger.debug(f"Platform {gpl_id} has pre-built mapping: {size_mb:.1f}MB")
                return size_mb

            # Try annotation file size first (smaller)
            annot_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/annot/{gpl_id}.annot.gz"
            try:
                annot_response = await self.client.head(annot_url, timeout=10.0)
                if annot_response.status_code == 200:
                    content_length = int(annot_response.headers.get('content-length', 0))
                    size_mb = content_length / (1024 * 1024)
                    logger.debug(f"Platform {gpl_id} annot size: {size_mb:.1f}MB")
                    return size_mb
            except (httpx.TimeoutException, httpx.ConnectError):
                pass

            # Fallback to family file size
            family_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/soft/{gpl_id}_family.soft.gz"
            head_response = await self.client.head(family_url, timeout=10.0)

            if head_response.status_code == 200:
                content_length = int(head_response.headers.get('content-length', 0))
                size_mb = content_length / (1024 * 1024)
                logger.debug(f"Platform {gpl_id} size: {size_mb:.1f}MB")
                return size_mb
            else:
                logger.debug(f"Could not determine size for platform {gpl_id} (HTTP {head_response.status_code})")
                return None
                
        except Exception as e:
            logger.debug(f"Error getting platform size for {platform_id}: {e}")
            return None