#!/usr/bin/env python3
"""
Test script to verify gene mapping service works with fixed URLs
"""

import asyncio
import sys
from app.services.gene_mapping_service import GeneMappingService

async def test_gene_mapping():
    """Test gene mapping with platforms that were failing"""
    service = GeneMappingService()
    
    # Test platforms that were failing in the logs
    test_platforms = [
        "GPL13912",  # Was failing before
        "GPL18752",  # Was failing before
        "GPL11180",  # Was failing before
    ]
    
    results = {}
    for platform_id in test_platforms:
        print(f"\nTesting {platform_id}...")
        try:
            mapping = await service.get_probe_to_gene_mapping(platform_id, use_cache=False)
            if mapping:
                results[platform_id] = {
                    "status": "success",
                    "probes_mapped": len(mapping),
                    "sample": list(mapping.items())[:3]  # Show first 3 mappings
                }
                print(f"  ✓ Successfully fetched {len(mapping)} probe mappings")
                for probe, gene in list(mapping.items())[:3]:
                    print(f"    {probe} → {gene}")
            else:
                results[platform_id] = {"status": "no_mapping"}
                print("  ✗ No mapping available")
        except Exception as e:
            results[platform_id] = {"status": "error", "error": str(e)}
            print(f"  ✗ Error: {e}")
    
    await service.close()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    print(f"Successful: {success_count}/{len(test_platforms)}")
    
    for platform, result in results.items():
        status_str = "✓" if result["status"] == "success" else "✗"
        print(f"{status_str} {platform}: {result['status']}")
    
    return success_count == len(test_platforms)

if __name__ == "__main__":
    success = asyncio.run(test_gene_mapping())
    sys.exit(0 if success else 1)
