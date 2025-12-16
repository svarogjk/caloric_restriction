"""
Gene Mapping Service
Maps probe IDs to standardized gene symbols using GEO platform annotations
"""

import logging
import gzip
import asyncio
import json
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
    INVALID_PLATFORMS_FILE = CACHE_DIR / ".invalid_platforms.json"
    GEO_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/platforms"
    MAX_RETRIES = 1  # Reduced from 3 to 1 - single quick check is enough
    RETRY_BACKOFF = 1.5  # Exponential backoff multiplier
    
    def __init__(self):
        """Initialize gene mapping service"""
        self.CACHE_DIR.mkdir(exist_ok=True)
        # Path to pre-created parquet files from platform loading
        self.PREBUILT_PLATFORM_DIR = Path("platform_mappings")
        # Large timeout for downloading potentially multi-GB platform files
        # Will be overridden per-request with smart timeout calculation
        self.client = httpx.AsyncClient(timeout=600.0, follow_redirects=True)
        # Cache only platform IDs, not the actual mappings (to save memory)
        self._cached_platform_ids: set = set()
        # Small in-memory cache for recently accessed mappings (LRU-like)
        self._mapping_cache: Dict[str, Dict[str, str]] = {}
        self.MAX_CACHE_SIZE = 3  # Only keep 3 platforms in memory
        # Track known invalid platforms to avoid repeated failed attempts
        self._invalid_platforms: set = set()
        # Load list of previously cached platforms on init
        self._load_memory_cache_index()
        # Load list of known invalid platforms
        self._load_invalid_platforms_cache()
    
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
    
    def _load_invalid_platforms_cache(self) -> None:
        """Load list of known invalid platforms to avoid repeated failed attempts"""
        try:
            if self.INVALID_PLATFORMS_FILE.exists():
                with open(self.INVALID_PLATFORMS_FILE, 'r') as f:
                    cache_data = json.load(f)
                
                self._invalid_platforms = set(cache_data.get('invalid_platforms', []))
                if self._invalid_platforms:
                    logger.debug(f"Loaded {len(self._invalid_platforms)} known invalid platforms")
        except Exception as e:
            logger.debug(f"Could not load invalid platforms cache: {e}")
    
    def _save_invalid_platforms_cache(self) -> None:
        """Save list of invalid platforms to persistent storage"""
        try:
            cache_data = {
                'invalid_platforms': list(self._invalid_platforms)
            }
            with open(self.INVALID_PLATFORMS_FILE, 'w') as f:
                json.dump(cache_data, f)
            logger.debug(f"Saved invalid platforms cache: {len(self._invalid_platforms)} platforms")
        except Exception as e:
            logger.debug(f"Failed to save invalid platforms cache: {e}")
    
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
    
    def _get_prebuilt_parquet_path(self, platform_id: str) -> Optional[Path]:
        """Check if a pre-built gene mapping parquet file exists for this platform.
        
        Pre-built parquet files are created from full platform downloads and stored
        in the platform_mappings directory. They contain clean probe->gene mappings.
        
        Args:
            platform_id: Platform ID (e.g., 'GPL23038')
            
        Returns:
            Path to the parquet file if it exists, None otherwise
        """
        try:
            # Look for {platform_id}_gene_mapping.parquet
            prebuilt_path = self.PREBUILT_PLATFORM_DIR / f"{platform_id}_gene_mapping.parquet"
            if prebuilt_path.exists() and prebuilt_path.stat().st_size > 0:
                logger.info(f"Found pre-built parquet for {platform_id} at {prebuilt_path}")
                return prebuilt_path
        except Exception as e:
            logger.warning(f"Error checking for pre-built parquet for {platform_id}: {e}")
        
        return None

    def _load_from_prebuilt_parquet(self, platform_id: str, parquet_path: Path) -> Dict[str, str]:
        """Load gene mappings from a pre-built parquet file.
        
        Args:
            platform_id: Platform ID
            parquet_path: Path to the parquet file
            
        Returns:
            Dictionary mapping probe IDs to gene symbols
        """
        try:
            import pandas as pd
            
            logger.info(f"Loading {platform_id} from pre-built parquet: {parquet_path}")
            df = pd.read_parquet(parquet_path)
            
            # Create mapping from ID -> gene_symbol
            mapping = {}
            if "ID" in df.columns and "gene_symbol" in df.columns:
                # Convert to dict, handling NaN values
                for idx, row in df.iterrows():
                    probe_id = str(row["ID"])
                    gene_symbol = str(row["gene_symbol"])
                    if gene_symbol and gene_symbol != "nan":
                        mapping[probe_id] = gene_symbol
            
            logger.info(
                f"Loaded {len(mapping)} probe->gene mappings from pre-built parquet for {platform_id}"
            )
            return mapping
            
        except Exception as e:
            logger.error(f"Failed to load pre-built parquet for {platform_id}: {e}")
            raise
    
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
        
        Args:
            platform_ids: List of GEO platform IDs
            use_cache: Whether to use cached mappings
        
        Returns:
            Dictionary mapping platform_id -> mapping (or None if failed)
        """
        logger.info(f"Fetching mappings for {len(platform_ids)} platforms in parallel")
        
        # Use asyncio.gather to fetch all mappings concurrently
        results = await asyncio.gather(
            *[self.get_probe_to_gene_mapping(pid, use_cache) for pid in platform_ids],
            return_exceptions=False
        )
        
        # Return as dict mapping platform_id to result
        mappings = {pid: result for pid, result in zip(platform_ids, results)}
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
        # Check small in-memory cache first
        if platform_id in self._mapping_cache:
            logger.debug(f"Using in-memory cache for {platform_id}")
            return self._mapping_cache[platform_id]
        
        # Check for pre-built parquet files first (fast, local, pre-processed)
        prebuilt_path = self._get_prebuilt_parquet_path(platform_id)
        if prebuilt_path:
            try:
                mapping = self._load_from_prebuilt_parquet(platform_id, prebuilt_path)
                
                # Only keep small mappings in memory cache (< 100k entries)
                if len(mapping) < 100000:
                    self._mapping_cache[platform_id] = mapping
                    # Enforce max cache size - remove oldest if over limit
                    if len(self._mapping_cache) > self.MAX_CACHE_SIZE:
                        oldest = next(iter(self._mapping_cache))
                        del self._mapping_cache[oldest]
                        logger.debug(f"Evicted {oldest} from memory cache (size limit reached)")
                
                return mapping
            except Exception as e:
                logger.warning(f"Failed to load pre-built parquet for {platform_id}: {e}")
                # Fall through to try disk cache and then download
        
        # Try to load from platform mappings directory (don't keep in memory for large files)
        mapping_path = self.PREBUILT_PLATFORM_DIR / f"{platform_id}_gene_mapping.parquet"
        if use_cache and mapping_path.exists():
            try:
                mapping_df = pd.read_parquet(mapping_path)
                mapping = dict(zip(mapping_df['probe_id'], mapping_df['gene_symbol']))
                
                # Only keep small mappings in memory cache (< 100k entries)
                if len(mapping) < 100000:
                    self._mapping_cache[platform_id] = mapping
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
                timeout=180  # 3 minute timeout per platform
            )
        except asyncio.TimeoutError:
            logger.error(f"Platform mapping download timed out for {platform_id}")
            return None
        
        if mapping:
            # Only keep small mappings in memory
            if len(mapping) < 100000:
                self._mapping_cache[platform_id] = mapping
                # Enforce max cache size
                if len(self._mapping_cache) > self.MAX_CACHE_SIZE:
                    oldest = next(iter(self._mapping_cache))
                    del self._mapping_cache[oldest]
                    logger.debug(f"Evicted {oldest} from memory cache (size limit reached)")
            
            # Save to disk cache
            if use_cache:
                try:
                    await self._save_mapping_to_parquet(platform_id, mapping)
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
        # - GPL81 -> /geo/platforms/GPL8nnn/GPL81/soft/GPL81_family.soft.gz (edge case!)
        # - GPL6246 -> /geo/platforms/GPL6nnn/GPL6246/soft/GPL6246_family.soft.gz
        # Pattern: remove last 3 digits and append "nnn"
        
        if len(numeric_id) >= 4:
            # Standard case: 4 or more digits (e.g., 1261, 13912, 6246)
            folder_prefix = f"GPL{numeric_id[:-3]}nnn"
        elif len(numeric_id) == 3:
            # 3 digits (e.g., 081 from GPL81 padded, or 100)
            folder_prefix = f"GPL{numeric_id[0]}nnn"
        elif len(numeric_id) == 2:
            # 2 digits (e.g., 81 from GPL81) - map to GPL8nnn
            folder_prefix = f"GPL{numeric_id[0]}nnn"
        else:
            # 1 digit fallback
            folder_prefix = f"GPL{numeric_id}nnn"
        
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
        
        # Mark platform as invalid if we failed to fetch it
        self._invalid_platforms.add(platform_id)
        self._save_invalid_platforms_cache()
        
        logger.warning(f"Failed to fetch mapping for {gpl_id} after {self.MAX_RETRIES} retries")
        return None
    
    async def _fetch_with_retry(self, gpl_id: str, folder_prefix: str) -> Optional[Dict[str, str]]:
        """
        Attempt to fetch platform mapping, trying both family and miniml formats.
        Uses smart timeout that accounts for file size (can be several GB).
        
        Args:
            gpl_id: GPL ID
            folder_prefix: Folder prefix for FTP path
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if both formats fail
        """
        # Try family format first with dynamic timeout based on file size
        family_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/soft/{gpl_id}_family.soft.gz"
        
        try:
            logger.debug(f"Downloading GPL file from: {family_url}")
            # First, get file size via HEAD request to determine timeout
            try:
                head_response = await self.client.head(family_url, timeout=10.0)
                file_size = int(head_response.headers.get('content-length', 0))
                
                # Calculate timeout dynamically based on file size
                # Estimate: ~10-15 MB/sec average download speed for large files
                # Conservative: double the time + buffer for connection/parsing
                # Can handle files up to 5GB+ without hard limits
                if file_size > 0:
                    # Base calculation: bytes / (10 MB/sec) to seconds
                    base_timeout = (file_size / (1024 * 1024)) / 10.0
                    # Add multiplier for safety and connection overhead
                    timeout_seconds = base_timeout * 2.0 + 60.0
                    # Cap at 20 minutes for extremely large files
                    timeout_seconds = min(timeout_seconds, 1200.0)
                    logger.debug(f"File size: {file_size / (1024*1024*1024):.2f}GB, calculated timeout: {timeout_seconds:.1f}s")
                else:
                    timeout_seconds = 600.0  # 10 minutes default fallback
            except Exception as e:
                logger.debug(f"Could not determine file size, using default timeout: {e}")
                timeout_seconds = 600.0  # 10 minute default timeout for unknown file sizes
            
            # Use httpx Timeout with separate connect and read timeouts
            http_timeout = httpx.Timeout(timeout=timeout_seconds, connect=30.0)
            
            logger.debug(f"Downloading {gpl_id} with timeout: {timeout_seconds:.1f}s")
            response = await self.client.get(family_url, timeout=http_timeout)
            
            if response.status_code == 200:
                # Decompress and parse with timeout
                try:
                    logger.debug(f"Decompressing and parsing {gpl_id}...")
                    content = gzip.decompress(response.content).decode('utf-8', errors='ignore')
                    mapping = self._parse_gpl_file(content, gpl_id)
                    
                    if mapping:
                        logger.info(f"Successfully fetched mapping for {gpl_id}: {len(mapping)} probes")
                        return mapping
                except asyncio.TimeoutError:
                    logger.error(f"Timeout decompressing/parsing {gpl_id}")
                    return None
        
        except asyncio.TimeoutError:
            logger.error(f"Download timeout for {gpl_id} from {family_url}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching family format for {gpl_id}: {e}")
        
        # Try miniml format as fallback (only if family format failed)
        logger.debug(f"Trying miniml format for {gpl_id}...")
        miniml_result = await self._try_miniml_format(gpl_id, folder_prefix)
        if miniml_result:
            return miniml_result
        
        return None
    
    def _parse_gpl_file(self, content: str, platform_id: str) -> Optional[Dict[str, str]]:
        """
        Parse GPL family file line-by-line and extract probe ID -> gene symbol mapping.
        Uses streaming approach to minimize memory usage.
        Implements multiple fallback strategies for column detection.
        
        Args:
            content: Content of GPL family SOFT file
            platform_id: Platform ID for logging
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol
        """
        try:
            mapping = {}
            lines_processed = 0
            table_started = False
            id_idx = None
            symbol_idx = None
            
            # Process line by line instead of loading entire file
            for line in content.split('\n'):
                lines_processed += 1
                
                # Skip empty lines and comment-only lines
                if not line or line.startswith('#!') or line.startswith('##'):
                    continue
                
                # Find table header line (starts with #ID)
                if line.startswith('#ID') and not table_started:
                    table_started = True
                    headers = line.split('\t')
                    
                    logger.debug(f"Found header at line {lines_processed}: {[h.lstrip('#') for h in headers[:10]]}")
                    
                    # First pass: look for exact matches
                    for idx, header in enumerate(headers):
                        header_clean = header.lstrip('#').upper().strip()
                        
                        if header_clean in ['ID', 'ID_REF', 'PROBE_ID', 'SEQUENCE_ACCESSION']:
                            id_idx = idx
                        elif header_clean in ['GENE_SYMBOL', 'SYMBOL', 'GENE_NAME']:
                            symbol_idx = idx
                    
                    # Second pass: flexible matching for ID column
                    if id_idx is None:
                        for idx, header in enumerate(headers):
                            header_clean = header.lstrip('#').upper()
                            if any(x in header_clean for x in ['ID', 'ACCESSION', 'PROBE']):
                                id_idx = idx
                                break
                    
                    # Third pass: flexible matching for gene symbol column
                    if symbol_idx is None:
                        for idx, header in enumerate(headers):
                            header_clean = header.lstrip('#').upper()
                            # Check for gene-related columns (symbol, name, description, etc.)
                            if any(x in header_clean for x in ['GENE_SYMBOL', 'GENE_NAME', 'SYMBOL', 
                                                                 'GENE', 'DESCRIPTION', 'PRODUCT']):
                                symbol_idx = idx
                                break
                    
                    # Fourth pass: use common aliases
                    if symbol_idx is None:
                        for idx, header in enumerate(headers):
                            header_clean = header.lstrip('#').upper()
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
            
            if mapping:
                logger.info(f"Parsed GPL file for {platform_id}: {len(mapping)} probes from {lines_processed} lines")
            else:
                logger.warning(f"No valid mappings found in GPL file for {platform_id} ({lines_processed} lines processed)")
            
            return mapping if mapping else None
        
        except Exception as e:
            logger.error(f"Error parsing GPL file for {platform_id}: {e}")
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
            if len(numeric_id) >= 4:
                folder_prefix = f"GPL{numeric_id[:-3]}nnn"
            elif len(numeric_id) == 3:
                folder_prefix = f"GPL{numeric_id[0]}nnn"
            elif len(numeric_id) == 2:
                folder_prefix = f"GPL{numeric_id[0]}nnn"
            else:
                folder_prefix = f"GPL{numeric_id}nnn"
            
            family_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/soft/{gpl_id}_family.soft.gz"
            
            # Get file size via HEAD request
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