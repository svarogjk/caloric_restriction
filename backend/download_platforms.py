#!/usr/bin/env python3
"""
Download and parse GPL platform mappings without timeouts.
Handles multiple platform formats including standard microarrays,
Affymetrix arrays with mrna_assignment, and sequencing platforms.
"""

import gzip
import re
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import httpx

# Configuration
PLATFORM_IDS = [
    "1261",    # Affymetrix Mouse Genome 430 2.0
    "13912",   # Agilent SurePrint G3 GE 8x60k  
    "16791",   # Illumina HiSeq 2500 (Homo sapiens) - SEQUENCING
    "17021",   # Illumina HiSeq 2500 (Mus musculus) - SEQUENCING
    "21185",   # Agilent-074809 SurePrint G3 Mouse GE v2 8x60K
    "23038",   # Affymetrix Mouse Gene 2.0 ST Array
    "24242",   # Affymetrix Mouse Gene 2.0 ST Array - subset
    "28271",   # Agilent-074809 SurePrint G3 Mouse GE v2 8x60K
]

CACHE_DIR = Path("platform_mappings")
BASE_URL = "https://ftp.ncbi.nlm.nih.gov/geo/platforms"
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

# Create cache directory
CACHE_DIR.mkdir(exist_ok=True)

def get_platform_url(platform_id: str) -> str:
    """Get the download URL for a platform."""
    prefix = f"GPL{platform_id[:-3]}nnn"
    return f"{BASE_URL}/{prefix}/GPL{platform_id}/soft/GPL{platform_id}_family.soft.gz"

def download_platform(platform_id: str) -> Optional[Path]:
    """Download a platform file with progress reporting and no timeout."""
    url = get_platform_url(platform_id)
    cache_file = CACHE_DIR / f"GPL{platform_id}_family.soft.gz"
    
    if cache_file.exists():
        print(f"✓ GPL{platform_id} already cached ({cache_file.stat().st_size / 1024 / 1024:.1f}MB)")
        return cache_file
    
    print(f"\n📥 Downloading GPL{platform_id}...")
    
    try:
        with httpx.stream("GET", url, timeout=None, follow_redirects=True) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(cache_file, 'wb') as f:
                for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb_downloaded = downloaded / 1024 / 1024
                        mb_total = total_size / 1024 / 1024
                        print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f}MB)", end='', flush=True)
            
            print(f"\n✓ Downloaded GPL{platform_id} ({downloaded / 1024 / 1024:.1f}MB)")
            return cache_file
            
    except Exception as e:
        print(f"\n✗ Error downloading GPL{platform_id}: {e}")
        if cache_file.exists():
            cache_file.unlink()
        return None

def is_sequencing_platform(platform_id: str, file_path: Path) -> bool:
    """Check if platform is a sequencing platform (no probe mappings)."""
    with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '!Platform_technology' in line and 'sequencing' in line.lower():
                return True
            if '!platform_table_begin' in line:
                return False
    return False

def extract_gene_from_text(text: str) -> Optional[str]:
    """Extract gene symbol from various text formats."""
    if not text or text in ['---', 'NA', 'NULL', '', 'null', 'N/A']:
        return None
    
    # Try to find gene symbol in parentheses: "description (Symbol)"
    match = re.search(r'\(([A-Za-z0-9_-]+)\)', text)
    if match:
        symbol = match.group(1)
        if re.match(r'^[A-Z][A-Za-z0-9_-]*$', symbol):
            return symbol
    
    # Try RefSeq ID
    match = re.match(r'^(NM_\d+|XM_\d+|NR_\d+)', text)
    if match:
        return match.group(1)
    
    # Clean and validate as gene symbol
    text = re.split(r'[;,/|]', text)[0].strip()
    text = re.sub(r'\s*///.*$', '', text)
    text = re.sub(r'\s*\[.*?\]', '', text)
    text = text.strip('"').strip("'").strip()
    
    if text and re.match(r'^[A-Za-z0-9][A-Za-z0-9_\-\.]*$', text):
        return text
    
    return None

def find_columns(columns: List[str]) -> Tuple[Optional[int], List[Tuple[int, str]]]:
    """Find ID and gene-related columns."""
    id_patterns = ['ID', 'id', 'probe_id', 'probeset_id', 'probe', 'ID_REF']
    
    id_col = None
    gene_cols = []
    
    # Find ID column
    for i, col in enumerate(columns):
        col_clean = col.strip('#').strip()
        if col_clean.lower() in [p.lower() for p in id_patterns]:
            id_col = i
            break
    
    # Find all gene-related columns
    gene_keywords = ['gene', 'symbol', 'mrna', 'assignment', 'annotation']
    for i, col in enumerate(columns):
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in gene_keywords):
            gene_cols.append((i, col))
    
    return id_col, gene_cols

def parse_platform(platform_id: str, file_path: Path) -> Optional[Dict[str, str]]:
    """Parse platform file to extract probe-to-gene mappings."""
    print(f"\n🔍 Parsing GPL{platform_id}...")
    
    # Check if sequencing platform
    if is_sequencing_platform(platform_id, file_path):
        print(f"  ⚠️  Sequencing platform - no probe mappings needed")
        return {}  # Empty dict indicates success but no mappings
    
    mappings = {}
    
    with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
        in_table = False
        header_line = None
        id_col = None
        gene_cols = []
        lines_processed = 0
        
        for line in f:
            line = line.strip()
            lines_processed += 1
            
            if lines_processed % 100000 == 0:
                print(f"\r  Processed {lines_processed:,} lines, found {len(mappings):,} mappings...", end='', flush=True)
            
            if line.startswith('!platform_table_begin'):
                in_table = True
                continue
            
            if line.startswith('!platform_table_end'):
                break
            
            # Process header
            if in_table and header_line is None and not line.startswith('!'):
                header_line = line
                columns = [col.strip().strip('"') for col in line.split('\t')]
                
                id_col, gene_cols = find_columns(columns)
                
                print(f"\n  Found {len(columns)} columns")
                if id_col is not None:
                    print(f"  ✓ ID column: '{columns[id_col]}' at position {id_col}")
                if gene_cols:
                    for col_idx, col_name in gene_cols:
                        print(f"  • Gene column: '{col_name}' at position {col_idx}")
                
                if id_col is None or not gene_cols:
                    print(f"  ✗ Required columns not found")
                    return None
                
                continue
            
            # Process data rows
            if in_table and header_line and not line.startswith('!'):
                fields = line.split('\t')
                
                if len(fields) > id_col:
                    probe_id = fields[id_col].strip()
                    
                    if probe_id:
                        # Try each gene column until we find a valid gene
                        for col_idx, col_name in gene_cols:
                            if len(fields) > col_idx:
                                gene_text = fields[col_idx].strip()
                                gene_symbol = extract_gene_from_text(gene_text)
                                
                                if gene_symbol:
                                    mappings[probe_id] = gene_symbol
                                    break
    
    print(f"\n✓ Parsed GPL{platform_id}: {len(mappings):,} mappings")
    return mappings if mappings or mappings == {} else None

def save_mappings(platform_id: str, mappings: Dict[str, str]):
    """Save mappings to a TSV file."""
    if not mappings:  # Empty dict means sequencing platform
        return
    
    output_file = CACHE_DIR / f"GPL{platform_id}_mappings.tsv"
    
    with open(output_file, 'w') as f:
        f.write("probe_id\tgene_symbol\n")
        for probe_id, gene_symbol in sorted(mappings.items()):
            f.write(f"{probe_id}\t{gene_symbol}\n")
    
    print(f"💾 Saved {len(mappings):,} mappings to {output_file}")

def main():
    """Main processing function."""
    print("=" * 80)
    print("GPL Platform Mapping Downloader")
    print("=" * 80)
    
    results = {}
    
    for platform_id in PLATFORM_IDS:
        print(f"\n{'=' * 80}")
        print(f"Processing GPL{platform_id}")
        print(f"{'=' * 80}")
        
        # Check if already processed
        mapping_file = CACHE_DIR / f"GPL{platform_id}_mappings.tsv"
        if mapping_file.exists():
            line_count = sum(1 for _ in open(mapping_file)) - 1
            print(f"✓ GPL{platform_id} already processed ({line_count:,} mappings)")
            results[platform_id] = "cached"
            continue
        
        # Download
        file_path = download_platform(platform_id)
        if not file_path:
            results[platform_id] = "download_failed"
            continue
        
        # Parse
        mappings = parse_platform(platform_id, file_path)
        if mappings is None:
            results[platform_id] = "parse_failed"
            continue
        
        # Save
        if mappings or mappings == {}:
            if mappings:
                save_mappings(platform_id, mappings)
            results[platform_id] = "success"
        
        time.sleep(1)
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    
    for platform_id in PLATFORM_IDS:
        status = results.get(platform_id, "not_processed")
        emoji = {
            "success": "✓",
            "cached": "✓",
            "download_failed": "✗",
            "parse_failed": "⚠",
        }.get(status, "○")
        
        print(f"{emoji} GPL{platform_id}: {status}")
    
    print(f"\n💾 All mappings saved to: {CACHE_DIR.absolute()}")

if __name__ == "__main__":
    main()