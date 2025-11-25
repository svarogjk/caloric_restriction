"""
Gene Mapping Service
Maps probe IDs to standardized gene symbols using GEO platform annotations
"""

import logging
import gzip
import asyncio
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
    GEO_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/platforms"
    MAX_RETRIES = 3
    RETRY_BACKOFF = 1.5  # Exponential backoff multiplier
    
    def __init__(self):
        """Initialize gene mapping service"""
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.client = httpx.AsyncClient(timeout=300.0, follow_redirects=True)
        # Cache of platform -> {probe_id -> gene_symbol}
        self._mapping_cache: Dict[str, Dict[str, str]] = {}
    
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
        Get mapping from probe IDs to gene symbols for a platform
        
        Args:
            platform_id: GEO platform ID (e.g., "GPL1261")
            use_cache: Whether to use cached mapping
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if failed
        """
        # Check memory cache first
        if platform_id in self._mapping_cache:
            logger.debug(f"Using cached mapping for {platform_id}")
            return self._mapping_cache[platform_id]
        
        # Try to load from disk cache
        cache_path = self.CACHE_DIR / f"{platform_id}.parquet"
        if use_cache and cache_path.exists():
            try:
                mapping_df = pd.read_parquet(cache_path)
                mapping = dict(zip(mapping_df['probe_id'], mapping_df['gene_symbol']))
                self._mapping_cache[platform_id] = mapping
                logger.info(f"Loaded mapping for {platform_id} from cache: {len(mapping)} probes")
                return mapping
            except Exception as e:
                logger.warning(f"Failed to load cached mapping for {platform_id}: {e}")
                pass
        
        # Fetch from GEO
        mapping = await self._fetch_platform_mapping(platform_id)
        
        if mapping:
            self._mapping_cache[platform_id] = mapping
            # Save to cache
            if use_cache:
                try:
                    mapping_df = pd.DataFrame([
                        {'probe_id': k, 'gene_symbol': v}
                        for k, v in mapping.items()
                    ])
                    mapping_df.to_parquet(cache_path, index=False)
                    logger.info(f"Saved mapping for {platform_id} to cache")
                except Exception as e:
                    logger.warning(f"Failed to save cache for {platform_id}: {e}")
        
        return mapping
    
    async def _fetch_platform_mapping(self, platform_id: str) -> Optional[Dict[str, str]]:
        """
        Fetch platform mapping from GEO with retry logic
        
        Args:
            platform_id: Platform ID (e.g., "GPL1261" or "1261" or "13912")
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if failed
        """
        logger.info(f"Fetching platform mapping for {platform_id}")
        
        # Normalize platform_id to GPL format
        if platform_id.startswith("GPL"):
            gpl_id = platform_id
            numeric_id = platform_id[3:]  # Remove "GPL" prefix
        else:
            numeric_id = platform_id
            gpl_id = f"GPL{platform_id}"
        
        # Construct URL to GEO FTP location
        # GEO FTP structure: /geo/platforms/GPLnnn/GPLXXXX/soft/
        # Examples:
        # - GPL1261 -> /geo/platforms/GPL1nnn/GPL1261/soft/GPL1261_family.soft.gz
        # - GPL13912 -> /geo/platforms/GPL13nnn/GPL13912/soft/GPL13912_family.soft.gz
        # - GPL6246 -> /geo/platforms/GPL6nnn/GPL6246/soft/GPL6246_family.soft.gz
        # Pattern: take all digits except last 3 and append "nnn"
        if len(numeric_id) >= 3:
            folder_prefix = f"GPL{numeric_id[:-3]}nnn"
        else:
            # Fallback for very short IDs (unlikely)
            folder_prefix = f"GPL{numeric_id}nnn"
        
        # Try with retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                mapping = await self._fetch_with_retry(gpl_id, folder_prefix)
                if mapping:
                    return mapping
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = (self.RETRY_BACKOFF ** attempt)
                    logger.debug(f"Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
        
        logger.warning(f"Failed to fetch mapping for {gpl_id} after {self.MAX_RETRIES} retries")
        return None
    
    async def _fetch_with_retry(self, gpl_id: str, folder_prefix: str) -> Optional[Dict[str, str]]:
        """
        Attempt to fetch platform mapping, trying both family and miniml formats
        
        Args:
            gpl_id: GPL ID
            folder_prefix: Folder prefix for FTP path
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol, or None if both formats fail
        """
        # Try family format first
        family_url = f"{self.GEO_FTP_BASE}/{folder_prefix}/{gpl_id}/soft/{gpl_id}_family.soft.gz"
        
        try:
            logger.debug(f"Downloading GPL file from: {family_url}")
            response = await self.client.get(family_url)
            
            if response.status_code == 200:
                # Decompress and parse
                content = gzip.decompress(response.content).decode('utf-8', errors='ignore')
                mapping = self._parse_gpl_file(content, gpl_id)
                
                if mapping:
                    logger.info(f"Successfully fetched mapping for {gpl_id}: {len(mapping)} probes")
                    return mapping
        
        except Exception as e:
            logger.debug(f"Error fetching family format for {gpl_id}: {e}")
        
        # Try miniml format as fallback
        logger.debug(f"Trying miniml format for {gpl_id}...")
        miniml_result = await self._try_miniml_format(gpl_id, folder_prefix)
        if miniml_result:
            return miniml_result
        
        return None
    
    def _parse_gpl_file(self, content: str, platform_id: str) -> Optional[Dict[str, str]]:
        """
        Parse GPL family file and extract probe ID -> gene symbol mapping
        
        Args:
            content: Content of GPL family SOFT file
            platform_id: Platform ID for logging
        
        Returns:
            Dictionary mapping probe_id -> gene_symbol
        """
        try:
            mapping = {}
            lines = content.split('\n')
            
            # Find the start of the table section
            table_start = None
            for i, line in enumerate(lines):
                if line.startswith('#ID'):
                    table_start = i
                    break
            
            if table_start is None:
                logger.debug(f"Could not find table start in GPL file for {platform_id}")
                return None
            
            # Parse header to find relevant columns
            header_line = lines[table_start]
            headers = header_line.split('\t')
            
            # Find indices for ID and gene symbol columns
            id_idx = None
            symbol_idx = None
            
            for idx, header in enumerate(headers):
                if header.startswith('#ID'):
                    id_idx = idx
                elif 'GENE_SYMBOL' in header.upper() or 'SYMBOL' in header.upper():
                    symbol_idx = idx
            
            if id_idx is None:
                logger.debug(f"Could not find ID column in GPL file for {platform_id}")
                return None
            
            # If no explicit gene symbol column, try common column names
            if symbol_idx is None:
                for idx, header in enumerate(headers):
                    if any(x in header.upper() for x in ['GENE', 'NAME', 'DESCRIPTION']):
                        symbol_idx = idx
                        break
            
            # Parse data rows
            for line in lines[table_start + 1:]:
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('\t')
                if len(parts) <= id_idx:
                    continue
                
                probe_id = parts[id_idx].strip()
                
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
                if gene_symbol and gene_symbol != '' and gene_symbol.lower() != 'null':
                    mapping[probe_id] = gene_symbol
            
            return mapping if mapping else None
        
        except Exception as e:
            logger.error(f"Error parsing GPL file for {platform_id}: {e}")
            return None
    
    async def _try_miniml_format(self, gpl_id: str, folder_prefix: str) -> Optional[Dict[str, str]]:
        """
        Try alternative miniml format for platform data
        
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
            
            # Look for .xml.gz files in miniml directory
            # This is a simplified approach - in practice, miniml files may have different structure
            logger.debug(f"Miniml directory exists but parsing miniml format not yet implemented")
            return None
            
        except Exception as e:
            logger.debug(f"Error trying miniml format for {gpl_id}: {e}")
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
