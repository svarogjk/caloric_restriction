#!/usr/bin/env python3
"""
Script to download and cache failed platform mappings.
These platforms failed during the workflow due to timeout/connection issues.
"""

import asyncio
import gzip
import logging
import io
from pathlib import Path
from typing import Dict, Optional, Set
import httpx
import pandas as pd
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Failed platforms that need to be downloaded
FAILED_PLATFORMS = [
    "17692",  # No XML files in miniml
    "17586",  # No XML files in miniml
    "16043",  # Peer closed connection
    "23985",  # Timeout during download
    "13497",  # Peer closed connection
    "27143",  # Peer closed connection
]

PLATFORM_MAPPINGS_DIR = Path(__file__).parent / "platform_mappings"
GEO_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/platforms"
CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks


class PlatformDownloader:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(600.0, connect=60.0),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.platform_dir = PLATFORM_MAPPINGS_DIR
        self.platform_dir.mkdir(exist_ok=True)
        
    async def close(self):
        await self.client.aclose()
    
    def _calculate_folder_prefix(self, platform_id: str) -> str:
        """Calculate GPL folder prefix (e.g., GPL17692 -> GPL17nnn)"""
        # Extract numeric part
        gpl_num = platform_id
        if len(gpl_num) >= 3:
            # Replace last 3 digits with 'nnn'
            prefix_num = gpl_num[:-3] + "nnn"
            return f"GPL{prefix_num}"
        return f"GPL{gpl_num}nnn"
    
    def _parse_annotation_file(self, content: bytes, platform_id: str) -> Dict[str, str]:
        """Parse annotation file content to extract probe->gene mappings"""
        mappings = {}
        
        try:
            # Decompress if gzipped
            if content.startswith(b'\x1f\x8b'):
                content = gzip.decompress(content)
            
            text = content.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            
            # Find header line with column names
            header_idx = None
            id_col = None
            symbol_col = None
            
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    continue
                if '\t' in line or ',' in line:
                    delimiter = '\t' if '\t' in line else ','
                    cols = line.strip().split(delimiter)
                    
                    # Look for ID and Gene Symbol columns
                    for idx, col in enumerate(cols):
                        col_lower = col.lower().strip()
                        if col_lower in ['id', 'probe_id', 'probeset_id']:
                            id_col = idx
                        elif any(name in col_lower for name in ['gene_symbol', 'gene symbol', 'symbol', 'gene_assignment', 'gene name']):
                            symbol_col = idx
                    
                    if id_col is not None and symbol_col is not None:
                        header_idx = i
                        logger.info(f"GPL{platform_id}: Found header at line {i}, ID col={id_col}, Symbol col={symbol_col}")
                        break
            
            if header_idx is None:
                logger.warning(f"GPL{platform_id}: Could not find header with ID and Symbol columns")
                return mappings
            
            # Parse data rows
            delimiter = '\t' if '\t' in lines[header_idx] else ','
            for i in range(header_idx + 1, len(lines)):
                line = lines[i].strip()
                if not line or line.startswith('#'):
                    continue
                
                cols = line.split(delimiter)
                if len(cols) <= max(id_col, symbol_col):
                    continue
                
                probe_id = cols[id_col].strip()
                gene_symbol = cols[symbol_col].strip()
                
                # Clean gene symbol
                if gene_symbol and gene_symbol not in ['---', 'NA', 'N/A', '']:
                    # Handle multiple genes separated by ///
                    if '///' in gene_symbol:
                        gene_symbol = gene_symbol.split('///')[0].strip()
                    mappings[probe_id] = gene_symbol
            
            logger.info(f"GPL{platform_id}: Parsed {len(mappings)} probe->gene mappings")
            
        except Exception as e:
            logger.error(f"GPL{platform_id}: Error parsing annotation file: {e}")
        
        return mappings
    
    async def _parse_soft_file_streaming(self, url: str, platform_id: str) -> Dict[str, str]:
        """Parse SOFT family file using streaming to avoid memory issues"""
        mappings = {}
        
        try:
            logger.info(f"GPL{platform_id}: Starting streaming download and parse...")
            
            async with self.client.stream('GET', url) as response:
                if response.status_code != 200:
                    logger.error(f"GPL{platform_id}: HTTP {response.status_code}")
                    return mappings
                
                # Stream and decompress the gzipped file chunk by chunk
                decompressor = gzip.GzipFile(fileobj=io.BytesIO())
                buffer = b''
                in_table = False
                id_col = None
                symbol_col = None
                lines_processed = 0
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                compressed_buffer = b''
                
                async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                    downloaded += len(chunk)
                    if downloaded % (100 * 1024 * 1024) < CHUNK_SIZE:  # Every 100MB
                        progress = (downloaded / total_size * 100) if total_size > 0 else 0
                        logger.info(f"GPL{platform_id}: {progress:.1f}% - {len(mappings)} mappings found")
                    
                    # Accumulate compressed data and try to decompress
                    compressed_buffer += chunk
                    
                    # Try to decompress the accumulated buffer
                    try:
                        decompressed = gzip.decompress(compressed_buffer)
                        compressed_buffer = b''  # Clear buffer after successful decompression
                    except Exception:
                        # Not enough data yet, continue accumulating
                        if len(compressed_buffer) > 50 * 1024 * 1024:  # If buffer > 50MB, try partial
                            try:
                                d = gzip.GzipFile(fileobj=io.BytesIO(compressed_buffer))
                                decompressed = d.read()
                                compressed_buffer = b''
                            except:
                                continue
                        else:
                            continue
                    
                    # Process line by line
                    buffer += decompressed
                    while b'\n' in buffer:
                        line_bytes, buffer = buffer.split(b'\n', 1)
                        
                        try:
                            line = line_bytes.decode('utf-8', errors='ignore').strip()
                        except:
                            continue
                        
                        lines_processed += 1
                        
                        if line.startswith('!platform_table_begin'):
                            in_table = True
                            logger.info(f"GPL{platform_id}: Found table start at line {lines_processed}")
                            continue
                        
                        if line.startswith('!platform_table_end'):
                            logger.info(f"GPL{platform_id}: Found table end at line {lines_processed}")
                            break
                        
                        if not in_table or not line or line.startswith('!') or line.startswith('#'):
                            continue
                        
                        # First data line is header
                        if id_col is None:
                            cols = line.split('\t')
                            for idx, col in enumerate(cols):
                                col_lower = col.lower().strip()
                                if col_lower in ['id', 'probe_id', 'probeset_id']:
                                    id_col = idx
                                elif any(name in col_lower for name in ['gene_symbol', 'symbol', 'orf', 'gene', 'entrezgeneid', 'genesymbol']):
                                    symbol_col = idx
                            
                            if id_col is not None and symbol_col is not None:
                                logger.info(f"GPL{platform_id}: Found columns - ID: {id_col}, Symbol: {symbol_col}")
                            continue
                        
                        # Parse data rows
                        if id_col is not None and symbol_col is not None:
                            cols = line.split('\t')
                            if len(cols) <= max(id_col, symbol_col):
                                continue
                            
                            probe_id = cols[id_col].strip()
                            gene_symbol = cols[symbol_col].strip()
                            
                            if gene_symbol and gene_symbol not in ['---', 'NA', 'N/A', '', 'null']:
                                if '///' in gene_symbol:
                                    gene_symbol = gene_symbol.split('///')[0].strip()
                                mappings[probe_id] = gene_symbol
                
                logger.info(f"GPL{platform_id}: Parsed {len(mappings)} probe->gene mappings from SOFT file")
                
        except Exception as e:
            logger.error(f"GPL{platform_id}: Error in streaming parse: {e}", exc_info=True)
        
        return mappings
    
    async def download_with_progress(self, url: str, platform_id: str) -> Optional[bytes]:
        """Download file with progress reporting"""
        try:
            async with self.client.stream('GET', url) as response:
                if response.status_code != 200:
                    logger.error(f"GPL{platform_id}: HTTP {response.status_code} for {url}")
                    return None
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunks = []
                
                logger.info(f"GPL{platform_id}: Downloading {total_size / 1024 / 1024:.1f}MB from {url}")
                
                async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if downloaded % (50 * 1024 * 1024) < CHUNK_SIZE:  # Log every 50MB
                            logger.info(f"GPL{platform_id}: Downloaded {progress:.1f}% ({downloaded / 1024 / 1024:.1f}MB)")
                
                content = b''.join(chunks)
                logger.info(f"GPL{platform_id}: Download complete - {len(content) / 1024 / 1024:.1f}MB")
                return content
                
        except Exception as e:
            logger.error(f"GPL{platform_id}: Download failed - {e}")
            return None
    
    async def try_download_platform(self, platform_id: str) -> Optional[Dict[str, str]]:
        """Try to download platform mapping using multiple strategies"""
        folder_prefix = self._calculate_folder_prefix(platform_id)
        logger.info(f"\n{'='*60}")
        logger.info(f"Downloading GPL{platform_id} (folder: {folder_prefix})")
        logger.info(f"{'='*60}")
        
        # Strategy 1: Try annotation file
        annot_url = f"{GEO_FTP_BASE}/{folder_prefix}/GPL{platform_id}/annot/GPL{platform_id}.annot.gz"
        logger.info(f"Strategy 1: Trying annotation file...")
        content = await self.download_with_progress(annot_url, platform_id)
        if content:
            mappings = self._parse_annotation_file(content, platform_id)
            if mappings:
                return mappings
        
        # Strategy 2: Try SOFT family file with streaming (for large files)
        soft_url = f"{GEO_FTP_BASE}/{folder_prefix}/GPL{platform_id}/soft/GPL{platform_id}_family.soft.gz"
        logger.info(f"Strategy 2: Trying SOFT family file (streaming mode)...")
        mappings = await self._parse_soft_file_streaming(soft_url, platform_id)
        if mappings:
            return mappings
        
        logger.error(f"GPL{platform_id}: All download strategies failed")
        return None
    
    def save_mappings(self, platform_id: str, mappings: Dict[str, str]):
        """Save mappings to parquet file"""
        try:
            df = pd.DataFrame({
                'probe_id': list(mappings.keys()),
                'gene_symbol': list(mappings.values())
            })
            
            output_file = self.platform_dir / f"{platform_id}_gene_mapping.parquet"
            df.to_parquet(output_file, index=False)
            logger.info(f"✓ GPL{platform_id}: Saved {len(mappings)} mappings to {output_file.name}")
            
        except Exception as e:
            logger.error(f"GPL{platform_id}: Failed to save mappings - {e}")
    
    async def download_all_platforms(self, platform_ids: list):
        """Download all failed platforms"""
        results = {}
        
        for platform_id in platform_ids:
            # Check if already exists
            existing_file = self.platform_dir / f"{platform_id}_gene_mapping.parquet"
            if existing_file.exists():
                logger.info(f"✓ GPL{platform_id}: Already exists - {existing_file}")
                try:
                    df = pd.read_parquet(existing_file)
                    results[platform_id] = "exists"
                    logger.info(f"  Contains {len(df)} mappings")
                except Exception as e:
                    logger.warning(f"  File exists but couldn't read: {e}")
                    results[platform_id] = "corrupted"
                continue
            
            # Try to download
            mappings = await self.try_download_platform(platform_id)
            if mappings:
                self.save_mappings(platform_id, mappings)
                results[platform_id] = "success"
            else:
                results[platform_id] = "failed"
            
            # Small delay between downloads
            await asyncio.sleep(2)
        
        return results


async def main():
    downloader = PlatformDownloader()
    
    try:
        logger.info("="*70)
        logger.info("Platform Mapping Download Script")
        logger.info("="*70)
        logger.info(f"Target platforms: {', '.join(['GPL' + p for p in FAILED_PLATFORMS])}")
        logger.info(f"Output directory: {downloader.platform_dir}")
        logger.info("="*70)
        
        results = await downloader.download_all_platforms(FAILED_PLATFORMS)
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("SUMMARY")
        logger.info("="*70)
        
        success_count = sum(1 for v in results.values() if v in ["success", "exists"])
        failed_count = sum(1 for v in results.values() if v == "failed")
        
        for platform_id, status in results.items():
            emoji = "✓" if status in ["success", "exists"] else "✗"
            logger.info(f"{emoji} GPL{platform_id}: {status}")
        
        logger.info("="*70)
        logger.info(f"Total: {success_count}/{len(FAILED_PLATFORMS)} platforms available")
        logger.info("="*70)
        
        if failed_count > 0:
            logger.warning(f"\n{failed_count} platforms still failed. May need manual intervention.")
            return 1
        else:
            logger.info("\n✓ All platforms successfully cached!")
            return 0
            
    finally:
        await downloader.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
