#!/usr/bin/env python3
"""
Preload Gene Mappings for Popular GEO Platforms

This script downloads and caches gene symbol mappings for the most commonly used
GEO platforms. This prevents slow downloads during analysis.

Only downloads the probe -> gene symbol mappings, not the full platform data.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.gene_mapping_service import GeneMappingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Most popular GEO platforms for expression profiling
# Source: https://www.ncbi.nlm.nih.gov/geo/browse/?view=platforms
# Focused on human and mouse expression arrays commonly used in survival/clinical studies

POPULAR_PLATFORMS = [
    # Human expression arrays (clinical/survival studies)
    "GPL570",    # Affymetrix Human Genome U133 Plus 2.0 Array (most popular, ~500K datasets)
    "GPL96",     # Affymetrix Human Genome U133A Array
    "GPL97",     # Affymetrix Human Genome U133B Array
    "GPL571",    # Affymetrix Human Genome U133A 2.0 Array
    "GPL6244",   # Affymetrix Human Gene 1.0 ST Array
    "GPL6480",   # Agilent-014850 Whole Human Genome Microarray 4x44K
    "GPL10558",  # Illumina HumanHT-12 V4.0 expression beadchip
    "GPL6884",   # Illumina HumanWG-6 v3.0 expression beadchip
    "GPL6947",   # Illumina HumanHT-12 V3.0 expression beadchip
    "GPL13667",  # Affymetrix Human Genome U219 Array
    "GPL17586",  # Affymetrix Human Transcriptome Array 2.0
    "GPL6102",   # Illumina human-6 v2.0 expression beadchip
    "GPL15207",  # Affymetrix Human Gene Expression Array
    "GPL16686",  # Affymetrix Human Gene 2.0 ST Array
    "GPL14550",  # Agilent-028004 SurePrint G3 Human GE 8x60K Microarray
    "GPL4133",   # Agilent-014850 Whole Human Genome Microarray 4x44K G4112F
    
    # Mouse expression arrays (aging/lifespan studies)
    "GPL1261",   # Affymetrix Mouse Genome 430 2.0 Array (most popular mouse)
    "GPL6246",   # Affymetrix Mouse Gene 1.0 ST Array
    "GPL81",     # Affymetrix Murine Genome U74A v2
    "GPL6887",   # Illumina MouseWG-6 v2.0 expression beadchip
    "GPL11180",  # Affymetrix HT MG-430 PM Array Plate
    "GPL6885",   # Illumina MouseRef-8 v2.0 expression beadchip
    "GPL7202",   # Agilent-014868 Whole Mouse Genome Microarray 4x44K
    "GPL21163",  # Agilent-074809 SurePrint G3 Mouse GE v2 8x60K Microarray
    "GPL16570",  # Affymetrix Mouse Gene 2.0 ST Array
    "GPL13912",  # Agilent-028005 SurePrint G3 Mouse GE 8x60K (if it has gene symbols)
    
    # Rat expression arrays
    "GPL1355",   # Affymetrix Rat Genome 230 2.0 Array
    "GPL6101",   # Illumina ratRef-12 v1.0 expression beadchip
    
    # Commonly used in aging research
    "GPL23038",  # Clariom S Human Array
    "GPL24242",  # Clariom S Mouse Array (transcriptome)
    "GPL21185",  # Agilent-072363 SurePrint G3 Yeast GE 8x60K
]

# Platforms known to have no gene symbol mappings (methylation arrays, etc.)
# These will be skipped
SKIP_PLATFORMS = {
    "GPL16791",  # Illumina HumanMethylation450 BeadChip - methylation, no gene symbols
    "GPL17021",  # Illumina HumanMethylation450 BeadChip - methylation, no gene symbols
    "GPL13534",  # Illumina HumanMethylation450 BeadChip
    "GPL21145",  # Illumina MethylationEPIC BeadChip
}

# Platforms known to have no annotation files (family files are multi-GB, impractical to download)
# These will be downloaded on-demand during analysis if needed
NO_ANNOTATION_FILE_PLATFORMS = {
    "GPL13667",  # 5.7GB family file
    "GPL17586",  # Large family file
    "GPL15207",  # Large family file  
    "GPL16686",  # Large family file
    "GPL14550",  # Large family file
    "GPL7202",   # Large family file
    "GPL21163",  # Large family file
    "GPL16570",  # Large family file
}

# Max time to wait for a single platform (in seconds)
PLATFORM_TIMEOUT = 120  # 2 minutes - should be enough for annotation files


async def preload_platform_mapping(
    service: GeneMappingService,
    platform_id: str
) -> tuple[str, bool, int]:
    """
    Preload gene mapping for a single platform.
    
    Returns:
        Tuple of (platform_id, success, num_mappings)
    """
    if platform_id in SKIP_PLATFORMS:
        logger.info(f"Skipping {platform_id} (known to have no gene mappings)")
        return (platform_id, False, 0)
    
    if platform_id in NO_ANNOTATION_FILE_PLATFORMS:
        logger.info(f"Skipping {platform_id} (no annotation file, family file too large)")
        return (platform_id, False, 0)
    
    try:
        logger.info(f"Loading gene mappings for {platform_id}...")
        # Add timeout to prevent blocking on large family file downloads
        mapping = await asyncio.wait_for(
            service.get_probe_to_gene_mapping(platform_id, use_cache=True),
            timeout=PLATFORM_TIMEOUT
        )
        
        if mapping:
            logger.info(f"  ✓ {platform_id}: {len(mapping):,} probe->gene mappings")
            return (platform_id, True, len(mapping))
        else:
            logger.warning(f"  ✗ {platform_id}: No mappings found (may be methylation/non-expression array)")
            return (platform_id, False, 0)
    
    except asyncio.TimeoutError:
        logger.warning(f"  ⏱ {platform_id}: Timeout - likely no annotation file, needs large family file")
        return (platform_id, False, 0)
            
    except Exception as e:
        logger.error(f"  ✗ {platform_id}: Error - {e}")
        return (platform_id, False, 0)


async def preload_all_platforms():
    """
    Preload gene mappings for all popular platforms.
    """
    logger.info("=" * 60)
    logger.info("Preloading Gene Mappings for Popular GEO Platforms")
    logger.info("=" * 60)
    logger.info(f"Total platforms to process: {len(POPULAR_PLATFORMS)}")
    logger.info(f"Platforms to skip (no gene symbols): {len(SKIP_PLATFORMS)}")
    logger.info(f"Platforms to skip (no annotation file): {len(NO_ANNOTATION_FILE_PLATFORMS)}")
    logger.info("")
    
    service = GeneMappingService()
    
    results = []
    successful = 0
    failed = 0
    total_mappings = 0
    
    # Process platforms sequentially to avoid overwhelming the server
    for i, platform_id in enumerate(POPULAR_PLATFORMS, 1):
        logger.info(f"[{i}/{len(POPULAR_PLATFORMS)}] Processing {platform_id}")
        
        platform_id, success, num_mappings = await preload_platform_mapping(service, platform_id)
        results.append((platform_id, success, num_mappings))
        
        if success:
            successful += 1
            total_mappings += num_mappings
        else:
            failed += 1
        
        # Small delay between platforms to be nice to the server
        if i < len(POPULAR_PLATFORMS):
            await asyncio.sleep(1)
    
    # Close the HTTP client
    await service.close()
    
    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total platforms processed: {len(POPULAR_PLATFORMS)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total probe->gene mappings: {total_mappings:,}")
    logger.info("")
    
    # List successful platforms
    if successful > 0:
        logger.info("Successfully loaded platforms:")
        for platform_id, success, num_mappings in results:
            if success:
                logger.info(f"  {platform_id}: {num_mappings:,} mappings")
    
    # List failed platforms
    if failed > 0:
        logger.info("")
        logger.info("Failed platforms (may need manual investigation):")
        for platform_id, success, num_mappings in results:
            if not success:
                logger.info(f"  {platform_id}")
    
    # Check cache directory
    cache_dir = service.PREBUILT_PLATFORM_DIR
    if cache_dir.exists():
        files = list(cache_dir.glob("*.tsv")) + list(cache_dir.glob("*_gene_mapping.parquet"))
        logger.info("")
        logger.info(f"Cached mapping files in {cache_dir}:")
        for f in sorted(files):
            size_kb = f.stat().st_size / 1024
            logger.info(f"  {f.name}: {size_kb:.1f} KB")
    
    return successful, failed


def main():
    """Main entry point"""
    print("Starting platform mapping preload...")
    successful, failed = asyncio.run(preload_all_platforms())
    
    if failed > 0:
        print(f"\n⚠ {failed} platforms failed to load. Check logs for details.")
        sys.exit(1)
    else:
        print(f"\n✓ All {successful} platforms loaded successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
