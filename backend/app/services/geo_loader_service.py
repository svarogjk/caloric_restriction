"""
GEO Data Loader Service
AI-powered loading of GEO expression data with format detection
Each dataset may have different format - AI agent handles this
"""

import logging
import asyncio
import json
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

from app.config.logging_config import get_logger

logger = get_logger(__name__)

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
    title: str  # Dataset title
    platform: str  # Platform ID
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
    
    # Storage directory for processed datasets (relative to project root)
    DATASETS_DIR = Path("datasets")
    
    def __init__(self, model: str = "mistral"):
        """Initialize data loader with AI agent"""
        self.model = model
        
        self.DATASETS_DIR.mkdir(exist_ok=True)
        
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
        Load GEO dataset with AI-powered format detection.
        First checks datasets/ folder, if not found loads from GEO, maps genes, and stores in parquet format.
        
        Args:
            dataset: GEODataset to load
            use_cache: Whether to use stored dataset (always True, kept for API compatibility)
            normalize: Whether to normalize expression data
        
        Returns:
            LoadedGEOData or None if loading fails
        """
        logger.info(f"Loading dataset {dataset.accession}")
        
        # Check datasets folder first
        dataset_path = self.DATASETS_DIR / f"{dataset.accession}.parquet"
        if dataset_path.exists():
            logger.info(f"Loading from datasets folder: {dataset_path}")
            try:
                return self._load_from_storage(dataset_path, dataset)
            except Exception as e:
                logger.warning(f"Storage load failed: {e}, loading from source")
        
        # Load from GEO source
        logger.info(f"Dataset {dataset.accession} not found in storage, loading from GEO")
        
        # Try series matrix first (most structured format)
        loaded_data = await self._try_series_matrix(dataset)
        
        # If that fails, try supplementary files
        if loaded_data is None:
            loaded_data = await self._try_supplementary_files(dataset)
        
        if loaded_data is None:
            logger.error(f"Failed to load dataset {dataset.accession}: Could not retrieve any data files")
            return None
        
        # Validate data is not empty with detailed error reporting
        if loaded_data.expression_matrix.empty or len(loaded_data.expression_matrix) == 0:
            logger.error(f"Dataset {dataset.accession} has no expression data (empty matrix). "
                        f"Shape: {loaded_data.expression_matrix.shape}")
            return None
        
        if len(loaded_data.expression_matrix.columns) < 2:
            logger.error(f"Dataset {dataset.accession} has too few samples ({len(loaded_data.expression_matrix.columns)}). "
                        f"Minimum 2 samples required. Total genes: {len(loaded_data.expression_matrix)}")
            return None
        
        # Perform comprehensive data quality checks
        quality_issues = self._validate_data_quality(loaded_data, dataset.accession)
        if quality_issues:
            logger.warning(f"Dataset {dataset.accession} quality issues: {quality_issues}")
            # Don't reject - just warn, some issues may be acceptable
        
        # Normalize if requested
        if normalize:
            loaded_data = self._normalize_expression(loaded_data)
        
        # Calculate quality metrics
        loaded_data.quality_metrics = self._calculate_quality_metrics(loaded_data)
        
        # Apply gene symbol mapping
        loaded_data = await self.apply_gene_mapping(loaded_data)
        
        # Save to datasets folder
        self._save_to_storage(loaded_data)
        
        logger.info(f"Successfully loaded {dataset.accession}: "
                   f"{loaded_data.expression_matrix.shape[0]} genes, "
                   f"{loaded_data.expression_matrix.shape[1]} samples")
        
        return loaded_data
    
    async def _try_series_matrix(self, dataset: GEODataset) -> Optional[LoadedGEOData]:
        """Try loading from series matrix file"""
        url = dataset.series_matrix_url
        if not url:
            # Generate the URL from accession
            accession = dataset.accession
            folder_prefix = accession[:-3] + "nnn"  # GSE19188 -> GSE19nnn
            url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{folder_prefix}/{accession}/matrix/{accession}_series_matrix.txt.gz"
        
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
        characteristics_list = []  # Collect all characteristics_ch1 rows
        data_start = None
        data_end = None
        
        for i, line in enumerate(lines):
            # Extract sample metadata
            if line.startswith('!Sample_'):
                parts = line.split('\t')
                if len(parts) > 1:
                    key = parts[0].replace('!Sample_', '').strip()
                    values = [p.strip('"') for p in parts[1:]]
                    
                    # Handle multiple characteristics_ch1 rows - they contain different fields
                    # Each row has format: "field_name: value" for each sample
                    if key == 'characteristics_ch1':
                        characteristics_list.append(values)
                    else:
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
            
            # Process characteristics_ch1 - expand "field_name: value" into separate columns
            if characteristics_list:
                for char_values in characteristics_list:
                    if not char_values:
                        continue
                    # Extract field name from first non-empty value
                    field_name = None
                    for val in char_values:
                        if val and ':' in val:
                            field_name = val.split(':')[0].strip().lower().replace(' ', '_')
                            break
                    
                    if field_name:
                        # Extract values for each sample
                        parsed_values = []
                        for val in char_values:
                            if val and ':' in val:
                                parsed_values.append(val.split(':', 1)[1].strip())
                            else:
                                parsed_values.append(val)
                        
                        if len(parsed_values) == len(meta_df):
                            meta_df[field_name] = parsed_values
                            logger.debug(f"Extracted characteristic: {field_name}")
                
                logger.info(f"Expanded {len(characteristics_list)} characteristics into separate columns")
            
            return LoadedGEOData(
                accession=dataset.accession,
                title=dataset.title,
                platform=dataset.platform,
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
    
    def _validate_data_quality(self, data: LoadedGEOData, accession: str) -> List[str]:
        """
        Perform comprehensive data quality checks.
        
        Args:
            data: Loaded data to validate
            accession: Dataset accession for logging
        
        Returns:
            List of quality issues found (empty if all checks pass)
        """
        issues = []
        expr = data.expression_matrix
        
        # Check for excessive missing values
        missing_rate = expr.isna().sum().sum() / expr.size if expr.size > 0 else 0
        if missing_rate > 0.5:
            issues.append(f"High missing rate: {missing_rate:.1%} (>50%)")
        elif missing_rate > 0.1:
            issues.append(f"Moderate missing rate: {missing_rate:.1%} (>10%)")
        
        # Check for near-zero variance genes (potential issues)
        gene_vars = expr.var(axis=1)
        zero_var_count = (gene_vars < 1e-6).sum()
        if zero_var_count > 0:
            issues.append(f"Zero-variance genes: {zero_var_count} ({zero_var_count/len(expr)*100:.1f}%)")
        
        # Check for extreme value distributions
        value_range = expr.max().max() - expr.min().min()
        if value_range < 0.1:
            issues.append(f"Very narrow value range: {value_range:.6f} (potential normalization issue)")
        
        # Check for potential outlier samples
        sample_medians = expr.median(axis=0)
        sample_mad = (sample_medians - sample_medians.median()).abs().median()
        
        if sample_mad > 0:
            outlier_threshold = sample_medians.median() + 3 * sample_mad
            outlier_samples = (sample_medians > outlier_threshold).sum()
            if outlier_samples > len(expr.columns) * 0.1:  # More than 10% are outliers
                issues.append(f"Potential outlier samples: {outlier_samples} ({outlier_samples/len(expr.columns)*100:.1f}%)")
        
        # Check for gene expression patterns
        gene_means = expr.mean(axis=1)
        if (gene_means < 1e-6).sum() > len(expr) * 0.5:
            issues.append(f"More than 50% of genes have near-zero mean expression")
        
        # Log individual checks for debugging
        logger.debug(f"{accession} quality metrics: "
                    f"Missing: {missing_rate:.1%}, "
                    f"Genes: {len(expr)}, "
                    f"Samples: {len(expr.columns)}, "
                    f"Value range: [{expr.min().min():.4f}, {expr.max().max():.4f}]")
        
        return issues
    
    def _save_to_storage(self, data: LoadedGEOData) -> None:
        """Save processed data to disk for quick reloading"""
        try:
            # Validate data before saving
            if data is None:
                logger.warning("Cannot save None data to storage")
                return
            
            if not hasattr(data, 'expression_matrix') or data.expression_matrix is None:
                logger.warning("Cannot save data without expression_matrix")
                return
            
            storage_path = Path("datasets") / f"{data.accession}.parquet"
            
            # Save expression matrix
            data.expression_matrix.to_parquet(storage_path)
            logger.debug(f"Saved expression matrix to: {storage_path}")
            
            # Save sample metadata - save DataFrame directly preserving index (sample IDs)
            meta_path = storage_path.with_name(f"{storage_path.stem}.metadata.parquet")
            if data.sample_metadata is not None and not data.sample_metadata.empty:
                data.sample_metadata.to_parquet(meta_path, index=True)
                logger.debug(f"Saved sample metadata to: {meta_path}")
            
            # Save loading strategy
            strategy_path = storage_path.with_name(f"{storage_path.stem}.strategy.json")
            strategy_dict = {
                'accession': data.accession,
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
            metrics_path = storage_path.with_name(f"{storage_path.stem}.metrics.json")
            with open(metrics_path, 'w') as f:
                json.dump(data.quality_metrics, f, indent=2)
            logger.debug(f"Saved quality metrics to: {metrics_path}")
            
            # Save gene mapping if available
            if data.probe_to_gene_mapping:
                mapping_path = storage_path.with_name(f"{storage_path.stem}.gene_mapping.parquet")
                mapping_df = pd.DataFrame([
                    {'probe_id': k, 'gene_symbol': v}
                    for k, v in data.probe_to_gene_mapping.items()
                ])
                mapping_df.to_parquet(mapping_path, index=False)
                logger.debug(f"Saved gene mapping to: {mapping_path}")
            
            logger.info(f"Successfully stored dataset {data.accession} to {storage_path}")
        except Exception as e:
            logger.warning(f"Failed to save to storage: {e}")
    
    def _old_save_to_storage(self, data: LoadedGEOData) -> None:
        """OLD UNUSED - DO NOT USE"""
        pass
    
    def _load_from_storage(self, storage_path: Path, dataset: GEODataset) -> LoadedGEOData:
        """Load data from datasets folder with metadata restoration"""
        try:
            # Load expression matrix
            expr_df = pd.read_parquet(storage_path)
            logger.debug(f"Loaded expression matrix from storage: {expr_df.shape}")
            
            # Load sample metadata
            meta_path = storage_path.with_name(f"{storage_path.stem}.metadata.parquet")
            meta_df = pd.read_parquet(meta_path) if meta_path.exists() else pd.DataFrame()
            logger.debug(f"Loaded sample metadata from storage: {meta_df.shape}")
            
            # Load loading strategy
            import json
            strategy_path = storage_path.with_name(f"{storage_path.stem}.strategy.json")
            strategy = DataLoadingStrategy(
                file_format="stored",
                separator="n/a",
                skip_rows=0,
                sample_id_column=None,
                expression_start_row=0,
                has_header=True,
                notes="Loaded from storage"
            )
            if strategy_path.exists():
                try:
                    with open(strategy_path, 'r') as f:
                        strategy_dict = json.load(f)
                    strategy = DataLoadingStrategy(**strategy_dict)
                    logger.debug(f"Restored loading strategy from storage")
                except Exception as e:
                    logger.debug(f"Could not restore strategy: {e}")
            
            # Load quality metrics
            metrics_path = storage_path.with_name(f"{storage_path.stem}.metrics.json")
            quality_metrics = {}
            if metrics_path.exists():
                try:
                    with open(metrics_path, 'r') as f:
                        quality_metrics = json.load(f)
                    logger.debug(f"Restored quality metrics from storage")
                except Exception as e:
                    logger.debug(f"Could not restore metrics: {e}")
            
            # Load gene mapping if available
            probe_to_gene_mapping = None
            mapping_path = storage_path.with_name(f"{storage_path.stem}.gene_mapping.parquet")
            if mapping_path.exists():
                try:
                    mapping_df = pd.read_parquet(mapping_path)
                    probe_to_gene_mapping = dict(zip(mapping_df['probe_id'], mapping_df['gene_symbol']))
                    logger.debug(f"Loaded gene mapping from storage: {len(probe_to_gene_mapping)} probes")
                except Exception as e:
                    logger.debug(f"Could not restore gene mapping: {e}")
            
            loaded_data = LoadedGEOData(
                accession=dataset.accession,
                title=dataset.title,
                platform=dataset.platform,
                expression_matrix=expr_df,
                sample_metadata=meta_df,
                platform_info={"platform": dataset.platform},
                loading_strategy=strategy,
                quality_metrics=quality_metrics,
                cache_path=storage_path,
                probe_to_gene_mapping=probe_to_gene_mapping
            )
            
            logger.info(f"Successfully loaded {dataset.accession} from storage")
            return loaded_data
            
        except Exception as e:
            logger.error(f"Failed to load from storage: {e}")
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
        
        platform_ids = data.platform_info.get('platforms', [])
        if not platform_ids:
            # Fallback to single platform field for backwards compatibility
            single_platform = data.platform_info.get('platform')
            platform_ids = [single_platform] if single_platform else []
        
        if not platform_ids:
            logger.warning(f"No platform IDs for {data.accession}, skipping gene mapping")
            return data
        
        logger.info(f"Fetching gene mappings for {len(platform_ids)} platform(s): {platform_ids}")
        
        try:
            # Try to get mappings for all platforms in order (combine all mappings)
            combined_mapping = {}
            
            for platform_id in platform_ids:
                if not platform_id:
                    continue
                    
                logger.debug(f"Trying platform {platform_id}")
                mapping = await self.gene_mapping_service.get_probe_to_gene_mapping(platform_id)
                
                if mapping:
                    combined_mapping.update(mapping)
                    # Convert probe IDs to string for matching (mapping keys are strings)
                    mapped_count = sum(1 for probe_id in data.expression_matrix.index if str(probe_id) in mapping)
                    logger.info(f"Platform {platform_id}: Mapped {mapped_count}/{len(data.expression_matrix)} probes")
            
            if combined_mapping:
                # Convert expression matrix index to string to match mapping keys
                data.expression_matrix.index = data.expression_matrix.index.astype(str)
                data.probe_to_gene_mapping = combined_mapping
                total_mapped = sum(1 for probe_id in data.expression_matrix.index if probe_id in combined_mapping)
                mapping_rate = 100.0 * total_mapped / len(data.expression_matrix) if data.expression_matrix.shape[0] > 0 else 0
                logger.info(f"Total mapped: {total_mapped}/{len(data.expression_matrix)} probes ({mapping_rate:.1f}%) for {data.accession}")
                
                # Log sample of mapped genes for verification
                sample_mappings = []
                for probe_id in list(data.expression_matrix.index)[:50]:  # Check first 50 probes
                    if probe_id in combined_mapping:
                        sample_mappings.append((probe_id, combined_mapping[probe_id]))
                        if len(sample_mappings) >= 10:
                            break
                
                if sample_mappings:
                    logger.info(f"Sample gene mappings for {data.accession}:")
                    for probe_id, gene_symbol in sample_mappings:
                        logger.info(f"  {probe_id} → {gene_symbol}")
                
                # Critical quality check: gene mapping success rate
                # If less than 20% of probes could be mapped, the analysis will fail
                if mapping_rate < 20.0:
                    logger.error(f"Gene mapping failure for {data.accession}: only {mapping_rate:.1f}% of probes mapped. Cannot proceed with analysis.")
                    return None
                
                return data
            else:
                # No mapping found for any platform - cannot proceed
                logger.error(f"Failed to fetch gene mappings for {data.accession}: No mappings found for platforms {platform_ids}")
                return None
        
        except Exception as e:
            logger.error(f"Error applying gene mapping: {e}")
            return None
    
    async def close(self):
        """Close HTTP client and gene mapping service"""
        await self.client.aclose()
        await self.gene_mapping_service.close()