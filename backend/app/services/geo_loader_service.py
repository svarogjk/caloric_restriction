"""
GEO Data Loader Service
AI-powered loading of GEO expression data with format detection
Each dataset may have different format - AI agent handles this
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import gzip
import io

import pandas as pd
import numpy as np
import httpx
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from app.models.llm_models import model_dict
from app.services.geo_client import GEODataset
from app.services.gene_mapping_service import GeneMappingService

logger = logging.getLogger(__name__)


class DataLoadingStrategy(BaseModel):
    """AI-determined strategy for loading dataset"""
    
    file_format: str = Field(
        description="Detected file format: series_matrix, supplementary_table, raw_counts"
    )
    separator: str = Field(
        description="Field separator: tab, comma, space"
    )
    skip_rows: int = Field(
        default=0,
        description="Number of rows to skip"
    )
    sample_id_column: Optional[str] = Field(
        None,
        description="Column name or index containing sample IDs"
    )
    expression_start_row: int = Field(
        default=0,
        description="Row where expression data starts"
    )
    has_header: bool = Field(
        default=True,
        description="Whether file has header row"
    )
    notes: str = Field(
        description="Additional parsing instructions"
    )
    
    @field_validator('skip_rows', 'expression_start_row', mode='before')
    @classmethod
    def coerce_int_fields(cls, v):
        """Coerce string integers to int"""
        if isinstance(v, str):
            try:
                return int(v)
            except (ValueError, TypeError):
                return 0
        elif v is None:
            return 0
        return v


@dataclass
class LoadedGEOData:
    """Container for loaded GEO expression data"""
    
    accession: str
    expression_matrix: pd.DataFrame  # Genes x Samples
    sample_metadata: pd.DataFrame  # Sample info
    platform_info: Dict[str, Any]
    loading_strategy: DataLoadingStrategy
    quality_metrics: Dict[str, float]
    cache_path: Optional[Path] = None
    probe_to_gene_mapping: Optional[Dict[str, str]] = None  # Probe ID -> Gene Symbol mapping


class GEODataLoaderService:
    """
    Service for loading GEO expression data with AI-powered format detection
    """
    
    CACHE_DIR = Path("/tmp/geo_cache")
    
    def __init__(self, model: str = "mistral"):
        """Initialize data loader with AI agent"""
        self.model = model
        
        self.CACHE_DIR.mkdir(exist_ok=True)
        
        self.format_agent = Agent(
            model=model_dict.get(self.model, model_dict["mistral"]),
            output_type=DataLoadingStrategy,
            system_prompt=self._get_format_detection_prompt(),
            retries=2,
        )
        
        self.client = httpx.AsyncClient(timeout=300.0, follow_redirects=True)
        self.gene_mapping_service = GeneMappingService()
    
    def set_model(self, model: str) -> None:
        """Update the model used by the format agent"""
        self.model = model
        self.format_agent = Agent(
            model=model_dict.get(self.model, model_dict["mistral"]),
            output_type=DataLoadingStrategy,
            system_prompt=self._get_format_detection_prompt(),
            retries=2,
        )
        logger.info(f"Updated loader service to use model: {model}")
    
    def _get_format_detection_prompt(self) -> str:
        """Get system prompt for format detection"""
        return """You are an expert at parsing GEO dataset files.

            GEO datasets come in various formats:

            1. SERIES MATRIX FILES (.txt.gz):
            - Start with metadata lines beginning with "!"
            - Expression data in tab-separated format
            - First column is ID_REF (gene/probe IDs)
            - Subsequent columns are samples
            - Usually skip ~50-70 lines to reach data

            2. SUPPLEMENTARY FILES:
            - Can be CSV, TSV, Excel
            - May have counts, FPKM, TPM, or normalized values
            - Variable header structures
            - May need to identify gene column and sample columns

            3. RAW COUNT FILES:
            - Usually tab-separated
            - Gene IDs in first column
            - Sample counts in subsequent columns
            - Minimal headers

            Your task: Analyze file preview and determine:
            - file_format: Which type above
            - separator: "\\t" (tab), "," (comma), or " " (space)
            - skip_rows: How many rows to skip
            - has_header: Whether header row exists
            - expression_start_row: Row index where actual data begins
            - notes: Any special handling needed

            Be precise - incorrect parsing will fail differential expression analysis."""
    
    async def load_dataset(
        self,
        dataset: GEODataset,
        use_cache: bool = True,
        normalize: bool = True
    ) -> Optional[LoadedGEOData]:
        """
        Load GEO dataset with AI-powered format detection
        
        Args:
            dataset: GEODataset to load
            use_cache: Whether to use cached data
            normalize: Whether to normalize expression data
        
        Returns:
            LoadedGEOData or None if loading fails
        """
        logger.info(f"Loading dataset {dataset.accession}")
        
        # Check cache first
        cache_path = self.CACHE_DIR / f"{dataset.accession}.parquet"
        if use_cache and cache_path.exists():
            logger.info(f"Loading from cache: {cache_path}")
            try:
                return self._load_from_cache(cache_path, dataset)
            except Exception as e:
                logger.warning(f"Cache load failed: {e}, loading from source")
        
        # Try series matrix first (most structured format)
        loaded_data = await self._try_series_matrix(dataset)
        
        # If that fails, try supplementary files
        if loaded_data is None:
            loaded_data = await self._try_supplementary_files(dataset)
        
        if loaded_data is None:
            logger.error(f"Failed to load dataset {dataset.accession}")
            return None
        
        # Validate data is not empty
        if loaded_data.expression_matrix.empty or len(loaded_data.expression_matrix) == 0:
            logger.error(f"Dataset {dataset.accession} has no expression data (empty matrix)")
            return None
        
        if len(loaded_data.expression_matrix.columns) < 2:
            logger.error(f"Dataset {dataset.accession} has too few samples ({len(loaded_data.expression_matrix.columns)})")
            return None
        
        # Normalize if requested
        if normalize:
            loaded_data = self._normalize_expression(loaded_data)
        
        # Calculate quality metrics
        loaded_data.quality_metrics = self._calculate_quality_metrics(loaded_data)
        
        # Apply gene symbol mapping
        loaded_data = await self.apply_gene_mapping(loaded_data)
        
        # Cache for future use
        if use_cache:
            self._save_to_cache(loaded_data, cache_path)
        
        logger.info(f"Successfully loaded {dataset.accession}: "
                   f"{loaded_data.expression_matrix.shape[0]} genes, "
                   f"{loaded_data.expression_matrix.shape[1]} samples")
        
        return loaded_data
    
    async def _try_series_matrix(self, dataset: GEODataset) -> Optional[LoadedGEOData]:
        """Try loading from series matrix file"""
        url = dataset.series_matrix_url
        if not url:
            return None
        
        logger.info(f"Trying series matrix: {url}")
        
        try:
            # Download file
            response = await self.client.get(url)
            if response.status_code != 200:
                logger.warning(f"Series matrix not available: {response.status_code}")
                return None
            
            # Decompress and preview
            content = gzip.decompress(response.content).decode('utf-8')
            preview_lines = content.split('\n')[:100]
            preview_text = '\n'.join(preview_lines)
            
            # Get AI strategy for parsing
            strategy = await self._get_loading_strategy(
                preview_text,
                dataset.accession,
                "series_matrix"
            )
            
            # Parse according to strategy
            return self._parse_series_matrix(content, dataset, strategy)
        
        except Exception as e:
            logger.error(f"Error loading series matrix: {e}")
            return None
    
    async def _try_supplementary_files(self, dataset: GEODataset) -> Optional[LoadedGEOData]:
        """Try loading from supplementary files"""
        # This would need to list and try supplementary files
        # For now, return None
        logger.info(f"Supplementary file loading not yet implemented for {dataset.accession}")
        return None
    
    async def _get_loading_strategy(
        self,
        file_preview: str,
        accession: str,
        file_type: str
    ) -> DataLoadingStrategy:
        """Use AI to determine loading strategy"""
        
        prompt = f"""Analyze this file preview from GEO dataset {accession} ({file_type}):

```
{file_preview}
```

Determine the optimal parsing strategy for this file."""
        
        try:
            result = await self.format_agent.run(prompt)
            strategy = result.output
            logger.info(f"AI loading strategy for {accession}: {strategy.file_format}, "
                       f"skip {strategy.skip_rows} rows")
            return strategy
        
        except Exception as e:
            logger.error(f"AI strategy detection failed: {e}, using defaults")
            return DataLoadingStrategy(
                file_format="series_matrix",
                separator="\t",
                skip_rows=0,
                sample_id_column=None,
                expression_start_row=0,
                has_header=True,
                notes="Default strategy due to AI failure"
            )
    
    def _parse_series_matrix(
        self,
        content: str,
        dataset: GEODataset,
        strategy: DataLoadingStrategy
    ) -> LoadedGEOData:
        """Parse series matrix file according to strategy"""
        lines = content.split('\n')
        logger.info(f"_parse_series_matrix, n_lines={len(lines)}")
        
        # Extract metadata and find data boundaries
        sample_metadata = {}
        data_start = None
        data_end = None
        
        for i, line in enumerate(lines):
            # Extract sample metadata
            if line.startswith('!Sample_'):
                parts = line.split('\t')
                if len(parts) > 1:
                    key = parts[0].replace('!Sample_', '').strip()
                    values = [p.strip('"') for p in parts[1:]]
                    sample_metadata[key] = values
            # Find data section markers
            elif line.startswith('!series_matrix_table_begin'):
                data_start = i + 1  # Data starts on next line
            elif line.startswith('!series_matrix_table_end'):
                data_end = i
                break
        
        if data_start is None:
            logger.error("Could not find !series_matrix_table_begin marker")
            raise ValueError("Invalid series matrix file format")
        
        if data_end is None:
            data_end = len(lines)
        
        logger.info(f"Extracting expression data from lines {data_start} to {data_end}")
        
        # Extract and parse expression data
        data_lines = lines[data_start:data_end]
        data_str = '\n'.join(data_lines)
        
        try:
            expr_df = pd.read_csv(
                io.StringIO(data_str),
                sep='\t',
                index_col=0
            )
            
            # Build sample metadata DataFrame
            if sample_metadata:
                meta_df = pd.DataFrame(sample_metadata)
                meta_df.index = expr_df.columns
            else:
                meta_df = pd.DataFrame(index=expr_df.columns)
            
            return LoadedGEOData(
                accession=dataset.accession,
                expression_matrix=expr_df,
                sample_metadata=meta_df,
                platform_info={"platform": dataset.platform},
                loading_strategy=strategy,
                quality_metrics={}
            )
        
        except Exception as e:
            logger.error(f"Error parsing series matrix: {e}")
            raise
    
    def _normalize_expression(self, data: LoadedGEOData) -> LoadedGEOData:
        """Normalize expression data with diagnostics"""
        
        expr = data.expression_matrix
        
        logger.info(f"Before normalization: min={expr.min().min():.2f}, max={expr.max().max():.2f}, "
                   f"median={expr.median().median():.2f}, NaN rate={expr.isna().sum().sum() / expr.size:.1%}")
        
        # Log2 transform if not already
        if expr.min().min() >= 0 and expr.max().max() > 100:
            logger.info("Applying log2 transformation")
            expr = np.log2(expr + 1)
        
        # Quantile normalization across samples
        logger.info("Applying quantile normalization")
        try:
            rank_mean = expr.stack().groupby(
                expr.rank(method='first').stack().astype(int)
            ).mean()
            expr_normalized = expr.rank(method='min').stack().astype(int).map(rank_mean).unstack()
            
            logger.info(f"After normalization: min={expr_normalized.min().min():.2f}, "
                       f"max={expr_normalized.max().max():.2f}, "
                       f"median={expr_normalized.median().median():.2f}")
            
            data.expression_matrix = expr_normalized
        except Exception as e:
            logger.warning(f"Quantile normalization failed: {e}. Using unnormalized data.")
            data.expression_matrix = expr
        
        return data
    
    def _calculate_quality_metrics(self, data: LoadedGEOData) -> Dict[str, float]:
        """Calculate data quality metrics"""
        
        expr = data.expression_matrix
        
        metrics = {
            "n_genes": len(expr),
            "n_samples": len(expr.columns),
            "missing_rate": expr.isna().sum().sum() / expr.size,
            "mean_expression": expr.mean().mean(),
            "cv_across_genes": (expr.std(axis=1) / expr.mean(axis=1)).mean(),
            "cv_across_samples": (expr.std(axis=0) / expr.mean(axis=0)).mean()
        }
        
        return metrics
    
    def _save_to_cache(self, data: LoadedGEOData, cache_path: Path):
        """Save data to cache with comprehensive metadata for session reuse"""
        try:
            # Save expression matrix
            data.expression_matrix.to_parquet(cache_path)
            logger.debug(f"Saved expression matrix to: {cache_path}")
            
            # Save sample metadata
            meta_path = cache_path.with_name(f"{cache_path.stem}.metadata.parquet")
            data.sample_metadata.to_parquet(meta_path)
            logger.debug(f"Saved sample metadata to: {meta_path}")
            
            # Save loading strategy as JSON for reproducibility
            strategy_path = cache_path.with_name(f"{cache_path.stem}.strategy.json")
            import json
            strategy_dict = {
                'file_format': data.loading_strategy.file_format,
                'separator': data.loading_strategy.separator,
                'skip_rows': data.loading_strategy.skip_rows,
                'sample_id_column': data.loading_strategy.sample_id_column,
                'expression_start_row': data.loading_strategy.expression_start_row,
                'has_header': data.loading_strategy.has_header,
                'notes': data.loading_strategy.notes
            }
            with open(strategy_path, 'w') as f:
                json.dump(strategy_dict, f, indent=2)
            logger.debug(f"Saved loading strategy to: {strategy_path}")
            
            # Save quality metrics
            metrics_path = cache_path.with_name(f"{cache_path.stem}.metrics.json")
            with open(metrics_path, 'w') as f:
                json.dump(data.quality_metrics, f, indent=2)
            logger.debug(f"Saved quality metrics to: {metrics_path}")
            
            # Save gene mapping if available
            if data.probe_to_gene_mapping:
                mapping_path = cache_path.with_name(f"{cache_path.stem}.gene_mapping.parquet")
                mapping_df = pd.DataFrame([
                    {'probe_id': k, 'gene_symbol': v}
                    for k, v in data.probe_to_gene_mapping.items()
                ])
                mapping_df.to_parquet(mapping_path, index=False)
                logger.debug(f"Saved gene mapping to: {mapping_path}")
            
            logger.info(f"Successfully cached dataset {data.accession} with all metadata")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _load_from_cache(self, cache_path: Path, dataset: GEODataset) -> LoadedGEOData:
        """Load data from cache with metadata restoration"""
        try:
            # Load expression matrix
            expr_df = pd.read_parquet(cache_path)
            logger.debug(f"Loaded expression matrix from cache: {expr_df.shape}")
            
            # Load sample metadata
            meta_path = cache_path.with_name(f"{cache_path.stem}.metadata.parquet")
            meta_df = pd.read_parquet(meta_path) if meta_path.exists() else pd.DataFrame()
            logger.debug(f"Loaded sample metadata from cache: {meta_df.shape}")
            
            # Load loading strategy
            import json
            strategy_path = cache_path.with_name(f"{cache_path.stem}.strategy.json")
            strategy = DataLoadingStrategy(
                file_format="cached",
                separator="n/a",
                skip_rows=0,
                sample_id_column=None,
                expression_start_row=0,
                has_header=True,
                notes="Loaded from cache"
            )
            if strategy_path.exists():
                try:
                    with open(strategy_path, 'r') as f:
                        strategy_dict = json.load(f)
                    strategy = DataLoadingStrategy(**strategy_dict)
                    logger.debug(f"Restored loading strategy from cache")
                except Exception as e:
                    logger.debug(f"Could not restore strategy: {e}")
            
            # Load quality metrics
            metrics_path = cache_path.with_name(f"{cache_path.stem}.metrics.json")
            quality_metrics = {}
            if metrics_path.exists():
                try:
                    with open(metrics_path, 'r') as f:
                        quality_metrics = json.load(f)
                    logger.debug(f"Restored quality metrics from cache")
                except Exception as e:
                    logger.debug(f"Could not restore metrics: {e}")
            
            # Load gene mapping if available
            probe_to_gene_mapping = None
            mapping_path = cache_path.with_name(f"{cache_path.stem}.gene_mapping.parquet")
            if mapping_path.exists():
                try:
                    mapping_df = pd.read_parquet(mapping_path)
                    probe_to_gene_mapping = dict(zip(mapping_df['probe_id'], mapping_df['gene_symbol']))
                    logger.debug(f"Loaded gene mapping from cache: {len(probe_to_gene_mapping)} probes")
                except Exception as e:
                    logger.debug(f"Could not restore gene mapping: {e}")
            
            loaded_data = LoadedGEOData(
                accession=dataset.accession,
                expression_matrix=expr_df,
                sample_metadata=meta_df,
                platform_info={"platform": dataset.platform},
                loading_strategy=strategy,
                quality_metrics=quality_metrics,
                cache_path=cache_path,
                probe_to_gene_mapping=probe_to_gene_mapping
            )
            
            logger.info(f"Successfully loaded {dataset.accession} from cache")
            return loaded_data
            
        except Exception as e:
            logger.error(f"Failed to load from cache: {e}")
            raise
    
    async def apply_gene_mapping(self, data: LoadedGEOData) -> LoadedGEOData:
        """
        Apply gene symbol mapping to loaded GEO data
        
        Args:
            data: Loaded GEO data with probe IDs
        
        Returns:
            Data with probe_to_gene_mapping populated
        """
        if not data.platform_info or 'platform' not in data.platform_info:
            logger.warning(f"No platform info for {data.accession}, skipping gene mapping")
            return data
        
        platform_id = data.platform_info['platform']
        if not platform_id or not isinstance(platform_id, str):
            logger.warning(f"Invalid platform ID for {data.accession}, skipping gene mapping")
            return data
        
        logger.info(f"Fetching gene mapping for platform {platform_id}")
        
        try:
            # Get probe ID to gene symbol mapping
            mapping = await self.gene_mapping_service.get_probe_to_gene_mapping(platform_id)
            
            if mapping:
                data.probe_to_gene_mapping = mapping
                mapped_count = sum(1 for probe_id in data.expression_matrix.index if probe_id in mapping)
                logger.info(f"Mapped {mapped_count}/{len(data.expression_matrix)} probes to gene symbols for {data.accession}")
                
                # Log sample of mapped genes for verification
                sample_mappings = []
                for probe_id in list(data.expression_matrix.index)[:50]:  # Check first 50 probes
                    if probe_id in mapping:
                        sample_mappings.append((probe_id, mapping[probe_id]))
                        if len(sample_mappings) >= 10:
                            break
                
                if sample_mappings:
                    logger.info(f"Sample gene mappings for {data.accession}:")
                    for probe_id, gene_symbol in sample_mappings:
                        logger.info(f"  {probe_id} → {gene_symbol}")
            else:
                logger.warning(f"Could not fetch gene mapping for platform {platform_id}")
            
            return data
        
        except Exception as e:
            logger.error(f"Error applying gene mapping: {e}")
            return data
    
    async def close(self):
        """Close HTTP client and gene mapping service"""
        await self.client.aclose()
        await self.gene_mapping_service.close()