#!/usr/bin/env python3
"""
Quick demo of cache functionality
Shows how caching dramatically speeds up repeated analyses
"""

import asyncio
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.cache_manager import CacheManager


async def demo():
    """Demonstrate cache benefits"""
    
    print("\n" + "=" * 70)
    print("GEO CACHE DEMO - Session Reuse Performance")
    print("=" * 70)
    
    # Check initial cache state
    print("\n1. Checking initial cache state...")
    initial_info = CacheManager.get_cache_info()
    print(f"   Cached datasets: {initial_info['total_cached_datasets']}")
    print(f"   Cache size: {initial_info['total_size_mb']} MB")
    
    if initial_info['total_cached_datasets'] > 0:
        print("\n   Currently cached datasets:")
        for ds in initial_info['datasets']:
            print(f"   • {ds['dataset_id']}: {ds['n_genes']} genes × {ds['n_samples']} samples")
    else:
        print("   No cached data yet. Running first analysis will populate cache...\n")
    
    # Show performance estimate
    speedup = CacheManager.estimate_analysis_speedup()
    print("\n2. Performance impact:")
    print(f"   Estimated speedup: {speedup['estimated_speedup']}")
    print(f"   Details: {speedup['details']}")
    
    # Show cache management options
    print("\n3. Cache management options:")
    print("   • View cache info: GET /api/cache/info")
    print("   • View platforms: GET /api/cache/platforms")
    print("   • Clear dataset: DELETE /api/cache/GSE272329")
    print("   • Clear all: DELETE /api/cache")
    
    # Show platform cache
    platform_info = CacheManager.get_platform_cache_info()
    print("\n4. Platform cache status:")
    print(f"   Cached platforms: {platform_info['total_cached_platforms']}")
    print(f"   Platform cache size: {platform_info['total_size_mb']} MB")
    
    if platform_info['platforms']:
        print("\n   Top cached platforms:")
        for pl in platform_info['platforms'][:5]:
            print(f"   • {pl['platform_id']}: {pl['n_probes']} probes ({pl['size_mb']} MB)")
    
    # Print full summary
    print("\n5. Full cache summary:")
    CacheManager.print_cache_summary()
    
    # Show what would happen with analysis
    print("\n6. Example: Running a search query")
    print("   First run (no cache):")
    print("   • Search GEO database: 2-5 seconds")
    print("   • Rank datasets: 10-20 seconds")
    print("   • Load 10 datasets from network: 50-150 seconds")
    print("   • Download platforms: 20-60 seconds")
    print("   • DE analysis: 30-60 seconds")
    print("   • Total: 112-295 seconds (~2-5 minutes)")
    
    print("\n   Subsequent runs (with cache):")
    print("   • Search GEO database: 2-5 seconds")
    print("   • Load 10 datasets from cache: 5-20 seconds")
    print("   • Use cached platforms: instant")
    print("   • DE analysis: 30-60 seconds")
    print("   • Total: 37-85 seconds (~1-1.5 minutes)")
    
    print("\n   Speedup: 3-7x faster on repeated queries!")
    
    print("\n" + "=" * 70)
    print("To use the cache system:")
    print("=" * 70)
    print("""
1. Start the backend server (cache is automatic):
   cd backend
   python -m uvicorn app.main:app --reload

2. Run searches - datasets are automatically cached:
   curl -X POST http://localhost:8000/api/search \\
     -H "Content-Type: application/json" \\
     -d '{
       "query": "caloric restriction aging",
       "model": "mistral",
       "max_datasets": 10
     }'

3. Check cache status:
   curl http://localhost:8000/api/cache/info

4. Run same search again - much faster! (from cache)
   
5. Clear cache if needed:
   curl -X DELETE http://localhost:8000/api/cache

For more details, see: CACHE_GUIDE.md
    """)
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(demo())
