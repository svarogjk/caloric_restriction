"""
Cache Manager Service
Utilities for managing local parquet cache of GEO datasets for session reuse
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import pandas as pd

logger = logging.getLogger(__name__)


class CacheManager:
    """Manage local cache of GEO datasets"""
    
    CACHE_DIR = Path("/tmp/geo_cache")
    GPL_CACHE_DIR = Path("/tmp/gpl_cache")
    
    @classmethod
    def get_cache_info(cls) -> Dict:
        """Get information about cached datasets"""
        info = {
            "geo_cache_dir": str(cls.CACHE_DIR),
            "gpl_cache_dir": str(cls.GPL_CACHE_DIR),
            "datasets": [],
            "total_size_mb": 0,
            "total_cached_datasets": 0
        }
        
        if not cls.CACHE_DIR.exists():
            return info
        
        # Find all cached datasets
        for cache_file in cls.CACHE_DIR.glob("GSE*.parquet"):
            try:
                dataset_id = cache_file.stem
                expr_df = pd.read_parquet(cache_file)
                
                # Get metadata if available
                meta_path = cache_file.with_name(f"{dataset_id}.metadata.parquet")
                meta_df = pd.read_parquet(meta_path) if meta_path.exists() else None
                
                # Get metrics if available
                metrics_path = cache_file.with_name(f"{dataset_id}.metrics.json")
                metrics = {}
                if metrics_path.exists():
                    with open(metrics_path, 'r') as f:
                        metrics = json.load(f)
                
                # Calculate size
                file_size_mb = cache_file.stat().st_size / (1024 * 1024)
                
                dataset_info = {
                    "dataset_id": dataset_id,
                    "n_genes": len(expr_df),
                    "n_samples": len(expr_df.columns),
                    "size_mb": round(file_size_mb, 2),
                    "has_metadata": meta_df is not None and len(meta_df) > 0,
                    "has_metrics": len(metrics) > 0,
                    "quality_metrics": metrics,
                    "cached_at": datetime.fromtimestamp(cache_file.stat().st_mtime).isoformat()
                }
                
                info["datasets"].append(dataset_info)
                info["total_size_mb"] += file_size_mb
                
            except Exception as e:
                logger.warning(f"Error reading cache info for {cache_file}: {e}")
        
        info["total_cached_datasets"] = len(info["datasets"])
        info["total_size_mb"] = round(info["total_size_mb"], 2)
        
        return info
    
    @classmethod
    def get_cached_dataset_ids(cls) -> List[str]:
        """Get list of all cached dataset IDs"""
        if not cls.CACHE_DIR.exists():
            return []
        
        ids = [f.stem for f in cls.CACHE_DIR.glob("GSE*.parquet")]
        return sorted(set(ids))
    
    @classmethod
    def is_dataset_cached(cls, dataset_id: str) -> bool:
        """Check if a dataset is cached"""
        cache_path = cls.CACHE_DIR / f"{dataset_id}.parquet"
        return cache_path.exists()
    
    @classmethod
    def get_dataset_cache_size(cls, dataset_id: str) -> float:
        """Get total cache size for a dataset in MB (including metadata)"""
        total_size = 0
        
        for cache_file in cls.CACHE_DIR.glob(f"{dataset_id}*"):
            try:
                total_size += cache_file.stat().st_size
            except Exception:
                pass
        
        return round(total_size / (1024 * 1024), 2)
    
    @classmethod
    def clear_dataset_cache(cls, dataset_id: str) -> bool:
        """Remove all cache files for a dataset"""
        try:
            for cache_file in cls.CACHE_DIR.glob(f"{dataset_id}*"):
                cache_file.unlink()
                logger.info(f"Deleted cache file: {cache_file}")
            
            logger.info(f"Cleared cache for dataset {dataset_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache for {dataset_id}: {e}")
            return False
    
    @classmethod
    @classmethod
    def clear_all_cache(cls) -> Dict:
        """Clear entire cache"""
        try:
            if cls.CACHE_DIR.exists():
                import shutil
                n_files = len(list(cls.CACHE_DIR.glob("*")))
                total_size = sum(f.stat().st_size for f in cls.CACHE_DIR.glob("*")) / (1024 * 1024)
                shutil.rmtree(cls.CACHE_DIR)
                cls.CACHE_DIR.mkdir(exist_ok=True)
                
                logger.info(f"Cleared all cache: {n_files} files, {total_size:.2f} MB")
                return {
                    "success": True,
                    "files_deleted": n_files,
                    "size_freed_mb": round(total_size, 2)
                }
            return {
                "success": True,
                "files_deleted": 0,
                "size_freed_mb": 0
            }
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    def get_platform_cache_info(cls) -> Dict:
        """Get information about cached platform files"""
        info = {
            "cache_dir": str(cls.GPL_CACHE_DIR),
            "platforms": [],
            "total_size_mb": 0,
            "total_cached_platforms": 0
        }
        
        if not cls.GPL_CACHE_DIR.exists():
            return info
        
        # Find all cached platform files
        for cache_file in cls.GPL_CACHE_DIR.glob("GPL*.parquet"):
            try:
                platform_id = cache_file.stem
                mapping_df = pd.read_parquet(cache_file)
                
                file_size_mb = cache_file.stat().st_size / (1024 * 1024)
                
                platform_info = {
                    "platform_id": platform_id,
                    "n_probes": len(mapping_df),
                    "size_mb": round(file_size_mb, 2),
                    "cached_at": datetime.fromtimestamp(cache_file.stat().st_mtime).isoformat()
                }
                
                info["platforms"].append(platform_info)
                info["total_size_mb"] += file_size_mb
                
            except Exception as e:
                logger.warning(f"Error reading platform cache info for {cache_file}: {e}")
        
        info["total_cached_platforms"] = len(info["platforms"])
        info["total_size_mb"] = round(info["total_size_mb"], 2)
        
        return info
    
    @classmethod
    def estimate_analysis_speedup(cls) -> Dict:
        """Estimate speedup from using cache"""
        cached_ids = cls.get_cached_dataset_ids()
        
        if not cached_ids:
            return {
                "cached_datasets": 0,
                "estimated_speedup": "No cache available",
                "details": "Caching data locally will dramatically speed up repeated analyses"
            }
        
        return {
            "cached_datasets": len(cached_ids),
            "dataset_ids": cached_ids,
            "estimated_speedup": "10-50x faster",
            "details": "Subsequent searches using cached datasets will skip network downloads and parsing, saving 5-30 seconds per dataset"
        }
    
    @classmethod
    def print_cache_summary(cls):
        """Print a formatted summary of cache status"""
        geo_info = cls.get_cache_info()
        platform_info = cls.get_platform_cache_info()
        speedup = cls.estimate_analysis_speedup()
        
        print("\n" + "=" * 70)
        print("CACHE SUMMARY")
        print("=" * 70)
        
        print(f"\nGEO DATASETS ({geo_info['total_cached_datasets']} cached)")
        print(f"Location: {geo_info['geo_cache_dir']}")
        print(f"Total size: {geo_info['total_size_mb']} MB")
        
        if geo_info['datasets']:
            print("\nCached datasets:")
            for ds in geo_info['datasets']:
                print(f"  • {ds['dataset_id']}: {ds['n_genes']} genes × {ds['n_samples']} samples "
                      f"({ds['size_mb']} MB)")
        
        print(f"\nPLATFORM MAPPINGS ({platform_info['total_cached_platforms']} cached)")
        print(f"Location: {platform_info['gpl_cache_dir']}")
        print(f"Total size: {platform_info['total_size_mb']} MB")
        
        if platform_info['platforms']:
            print("Cached platforms:")
            for pl in platform_info['platforms'][:10]:  # Show first 10
                print(f"  • {pl['platform_id']}: {pl['n_probes']} probes ({pl['size_mb']} MB)")
        
        print("\nPERFORMANCE IMPACT")
        print(f"Estimated speedup: {speedup['estimated_speedup']}")
        print(f"Details: {speedup['details']}")
        
        print("\n" + "=" * 70 + "\n")
