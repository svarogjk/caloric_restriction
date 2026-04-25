"""
Survival Analysis Service
Performs survival analysis on GEO datasets to identify genes associated with lifespan/longevity
"""

import logging
import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import warnings
from multiprocessing import Pool, cpu_count
from functools import partial

import pandas as pd
import numpy as np
from scipy import stats
from pydantic_ai import Agent
from pydantic import BaseModel, Field

from app.config.logging_config import get_logger
from app.services.geo_loader_service import LoadedGEOData
from app.utils.memory_tracker import track_memory, log_memory_checkpoint

logger = get_logger(__name__)
warnings.filterwarnings('ignore')

# Try to import survival analysis libraries
try:
    from lifelines import KaplanMeierFitter, CoxPHFitter
    from lifelines.statistics import logrank_test, multivariate_logrank_test
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False
    logger.warning("lifelines not installed. Install with: pip install lifelines")


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class KMCurveData:
    """Kaplan-Meier curve data for one expression group"""
    times: List[float]
    survival_probabilities: List[float]
    ci_lower: Optional[List[float]]
    ci_upper: Optional[List[float]]
    n_samples: int
    n_events: int


@dataclass
class GeneSurvivalResult:
    """Result of survival analysis for a single gene"""
    gene_id: str
    gene_symbol: Optional[str]
    hazard_ratio: float
    hazard_ratio_ci_lower: float
    hazard_ratio_ci_upper: float
    log_rank_p_value: float
    cox_p_value: float
    median_survival_high: Optional[float]  # Median survival for high expression group
    median_survival_low: Optional[float]   # Median survival for low expression group
    is_significant: bool
    expression_direction: str  # "high_risk" or "low_risk"
    n_samples_high: int
    n_samples_low: int
    # KM curve data for visualization
    km_curve_high: Optional[KMCurveData] = None
    km_curve_low: Optional[KMCurveData] = None
    # Multivariate Cox results (F13)
    adjusted_hazard_ratio: Optional[float] = None
    multivariate_cox_p: Optional[float] = None
    covariates_used: Optional[List[str]] = None


@dataclass 
class SurvivalAnalysisResult:
    """Complete survival analysis result for a dataset"""
    accession: str
    title: str
    platform: str
    n_samples: int
    n_genes_analyzed: int
    n_significant_genes: int
    significant_genes: List[GeneSurvivalResult]
    survival_time_unit: str  # "days", "months", "years"
    event_type: str  # "death", "recurrence", etc.
    analysis_method: str


class SurvivalDataDetectionResponse(BaseModel):
    """Response model for LLM survival data detection"""
    has_survival_data: bool = Field(
        ...,
        description="Whether the dataset contains survival/time-to-event data"
    )
    survival_time_column: Optional[str] = Field(
        default=None,
        description="Column name containing survival time (e.g., 'survival_days', 'time_to_death')"
    )
    event_column: Optional[str] = Field(
        default=None,
        description="Column name containing event status (e.g., 'death', 'event', 'status')"
    )
    survival_time_unit: str = Field(
        default="days",
        description="Unit of survival time: 'days', 'months', or 'years'"
    )
    event_type: str = Field(
        default="death",
        description="Type of event being measured"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of how survival data was identified"
    )
    covariate_columns: List[str] = Field(
        default_factory=list,
        description="Column names for clinical covariates (age, stage, grade, treatment) to use in multivariate Cox"
    )


def create_survival_detection_agent(model: str = "mistral") -> Agent:
    """Create LLM agent for survival data detection
    
    Args:
        model: Model to use ('anthropic' or 'mistral')
        
    Returns:
        Configured Agent instance
    """
    from app.models.llm_models import model_dict
    
    selected_model = model_dict.get(model)
    if selected_model is None:
        logger.warning(f"Model {model} not found, falling back to mistral")
        selected_model = model_dict.get("mistral")
    
    return Agent(
        model=selected_model,
        output_type=SurvivalDataDetectionResponse,
        system_prompt="""You are an expert in analyzing GEO dataset metadata to identify survival/time-to-event data.

Your task is to examine sample metadata and characteristics to determine if survival data is present.

Look for patterns like:
- Time-related columns: survival_time, time_to_death, follow_up_days, months_survival, os_time, rfs_time
- Event columns: death, deceased, alive, event, status, vital_status, os_event, rfs_event
- Age at death or lifespan data in animal studies
- Clinical outcome data with time components

For aging/lifespan studies:
- Look for age at death, lifespan, longevity measurements
- Treatment groups may have different survival outcomes
- Time units are often days or months for mouse studies

Return accurate column names that exist in the data.
If no survival data is present, set has_survival_data to false."""
    )


class SurvivalAnalysisService:
    """
    Service for performing survival analysis on gene expression data
    
    Identifies genes whose expression levels are associated with survival outcomes
    using Kaplan-Meier analysis and Cox proportional hazards regression.
    """
    
    def __init__(
        self,
        p_value_threshold: float = 0.05,
        hazard_ratio_threshold: float = 1.5,
        min_samples_per_group: int = 5,
        model: str = "mistral"
    ):
        """
        Initialize survival analysis service
        
        Args:
            p_value_threshold: Significance threshold for Cox regression p-value
            hazard_ratio_threshold: Minimum hazard ratio to consider meaningful
            min_samples_per_group: Minimum samples required per expression group
            model: LLM model for survival data detection
        """
        if not LIFELINES_AVAILABLE:
            raise ImportError("lifelines library required for survival analysis. "
                            "Install with: pip install lifelines")
        
        self.p_value_threshold = p_value_threshold
        self.hazard_ratio_threshold = hazard_ratio_threshold
        self.min_samples_per_group = min_samples_per_group
        self.model = model
        self._detection_agent = None
    
    def set_model(self, model: str):
        """Update the LLM model and recreate agent"""
        self.model = model
        self._detection_agent = None
    
    @property
    def detection_agent(self) -> Agent:
        """Lazy initialization of detection agent"""
        if self._detection_agent is None:
            self._detection_agent = create_survival_detection_agent(self.model)
        return self._detection_agent
    
    async def detect_survival_data(
        self,
        loaded_data: LoadedGEOData
    ) -> Optional[SurvivalDataDetectionResponse]:
        """
        Use LLM to detect if dataset contains survival data
        
        Args:
            loaded_data: Loaded GEO dataset
            
        Returns:
            Detection response with column information, or None if detection fails
        """
        if loaded_data.sample_metadata is None or loaded_data.sample_metadata.empty:
            logger.warning("No sample metadata available for survival detection")
            return None
        
        # Prepare metadata summary for LLM
        # sample_metadata is already a DataFrame with samples as rows
        metadata_df = loaded_data.sample_metadata
        
        # Log all column names for debugging
        logger.info(f"Checking {loaded_data.accession} metadata columns: {metadata_df.columns.tolist()}")
        
        # Quick pre-check for common survival-related column names
        survival_keywords = [
            'survival', 'os_time', 'os_event', 'pfs', 'rfs', 'dfs',
            'death', 'deceased', 'vital_status', 'alive', 'dead',
            'follow_up', 'followup', 'time_to', 'event', 'censor',
            'lifespan', 'longevity', 'age_at_death', 'days_survived',
            'overall_survival', 'status', 'recurrence', 'relapse'
        ]
        
        potential_survival_cols = []
        for col in metadata_df.columns:
            col_lower = col.lower()
            for keyword in survival_keywords:
                if keyword in col_lower:
                    potential_survival_cols.append(col)
                    break
        
        if potential_survival_cols:
            logger.info(f"Found potential survival columns in {loaded_data.accession}: {potential_survival_cols}")
        else:
            logger.info(f"No obvious survival columns found in {loaded_data.accession} column names")
        
        # Get column names and sample values
        columns_info = []
        for col in metadata_df.columns[:50]:  # Limit to first 50 columns
            sample_values = metadata_df[col].dropna().head(5).tolist()
            columns_info.append(f"  {col}: {sample_values}")
        
        prompt = f"""Analyze this GEO dataset metadata to identify survival/time-to-event data.

Dataset: {loaded_data.accession} - {loaded_data.title}

Sample metadata columns and example values:
{chr(10).join(columns_info)}

Determine if this dataset contains survival data and identify the relevant columns."""

        try:
            result = await self.detection_agent.run(prompt)
            return result.output
        except Exception as e:
            logger.error(f"Survival data detection failed: {e}")
            return None

    def detect_survival_data_regex(
        self,
        loaded_data: LoadedGEOData
    ) -> Optional[SurvivalDataDetectionResponse]:
        """
        Regex-based fallback for survival data detection.
        Scans column names and values for common survival patterns.
        Used when LLM detection fails or returns no results.
        """
        if loaded_data.sample_metadata is None or loaded_data.sample_metadata.empty:
            return None

        metadata_df = loaded_data.sample_metadata

        # Patterns for time columns (column name matching)
        time_patterns = [
            re.compile(r'(?:overall[_\s]?survival|os)[_\s]?(?:time|months?|days?|years?)', re.I),
            re.compile(r'(?:rfs|dfs|pfs|efs|dss)[_\s]?(?:time|months?|days?|years?)', re.I),
            re.compile(r'survival[_\s]?(?:time|months?|days?|years?)', re.I),
            re.compile(r'(?:time[_\s]?to[_\s]?(?:death|event|recurrence|relapse|progression))', re.I),
            re.compile(r'follow[_\s]?up[_\s]?(?:time|months?|days?|years?)', re.I),
            re.compile(r'(?:months?|days?|years?)[_\s]?(?:survival|follow)', re.I),
            re.compile(r'(?:age[_\s]?at[_\s]?death|lifespan|longevity)', re.I),
            re.compile(r'(?:os_time|rfs_time|dfs_time|pfs_time)', re.I),
            re.compile(r't\.(?:os|rfs|dfs|pfs)', re.I),
        ]

        # Patterns for event columns (column name matching)
        event_patterns = [
            re.compile(r'(?:overall[_\s]?survival|os)[_\s]?(?:event|status|censor)', re.I),
            re.compile(r'(?:rfs|dfs|pfs|efs|dss)[_\s]?(?:event|status|censor)', re.I),
            re.compile(r'vital[_\s]?status', re.I),
            re.compile(r'(?:death|deceased|dead|alive|living)', re.I),
            re.compile(r'(?:event|censor(?:ed)?|status)', re.I),
            re.compile(r'(?:os_event|rfs_event|dfs_event)', re.I),
            re.compile(r'e\.(?:os|rfs|dfs|pfs)', re.I),
            re.compile(r'(?:recurrence|relapse)[_\s]?(?:status|event)?', re.I),
        ]

        # Patterns for survival data embedded in values (e.g., "os (months): 24")
        value_time_patterns = [
            re.compile(r'(?:os|overall\s*survival|survival)\s*\(?(?:months?|days?|years?)\)?\s*:\s*[\d.]+', re.I),
            re.compile(r'(?:follow[\s_]?up|rfs|dfs|pfs)\s*\(?(?:months?|days?|years?)\)?\s*:\s*[\d.]+', re.I),
            re.compile(r'(?:time[\s_]?to[\s_]?(?:death|event))\s*:\s*[\d.]+', re.I),
            re.compile(r'(?:age[\s_]?at[\s_]?death|lifespan)\s*:\s*[\d.]+', re.I),
        ]
        value_event_patterns = [
            re.compile(r'(?:vital[\s_]?status|os[\s_]?status|status)\s*:\s*(?:dead|alive|deceased|living|0|1)', re.I),
            re.compile(r'(?:os[\s_]?event|event|death|deceased)\s*:\s*(?:0|1|yes|no|true|false)', re.I),
            re.compile(r'(?:dead|alive|deceased|living)\s*:\s*(?:0|1|yes|no)', re.I),
        ]

        time_col = None
        event_col = None
        time_unit = "days"

        # Phase 1: Match column names directly
        for col in metadata_df.columns:
            if time_col is None:
                for pattern in time_patterns:
                    if pattern.search(col):
                        time_col = col
                        # Infer time unit from column name
                        col_lower = col.lower()
                        if 'month' in col_lower:
                            time_unit = "months"
                        elif 'year' in col_lower:
                            time_unit = "years"
                        break
            if event_col is None:
                for pattern in event_patterns:
                    if pattern.search(col):
                        # Avoid matching generic "status" when there's no time col
                        if pattern.pattern == r'(?:event|censor(?:ed)?|status)' and time_col is None:
                            continue
                        event_col = col
                        break

        # Phase 2: Scan values in characteristics columns for embedded survival data
        if time_col is None or event_col is None:
            for col in metadata_df.columns:
                sample_values = metadata_df[col].dropna().head(10).astype(str).tolist()
                joined_values = " | ".join(sample_values)

                if time_col is None:
                    for pattern in value_time_patterns:
                        if pattern.search(joined_values):
                            time_col = col
                            if 'month' in joined_values.lower():
                                time_unit = "months"
                            elif 'year' in joined_values.lower():
                                time_unit = "years"
                            logger.info(f"Regex found survival time in values of column '{col}': {sample_values[:3]}")
                            break

                if event_col is None:
                    for pattern in value_event_patterns:
                        if pattern.search(joined_values):
                            event_col = col
                            logger.info(f"Regex found event status in values of column '{col}': {sample_values[:3]}")
                            break

        if time_col and event_col:
            # Validate: check that the time column has numeric-looking values
            try:
                time_vals = pd.to_numeric(metadata_df[time_col], errors='coerce')
                valid_count = time_vals.notna().sum()
                if valid_count < 5:
                    logger.debug(f"Regex detection rejected: time column '{time_col}' has only {valid_count} numeric values")
                    return None
            except (ValueError, TypeError):
                return None

            event_type = "death"
            for event_kw in ['recurrence', 'relapse', 'progression']:
                if event_kw in (event_col or '').lower():
                    event_type = event_kw
                    break

            covariate_cols = self._detect_covariate_columns(metadata_df, exclude={time_col, event_col})
            logger.info(f"Regex fallback detected survival data: time='{time_col}', event='{event_col}', unit={time_unit}")
            return SurvivalDataDetectionResponse(
                has_survival_data=True,
                survival_time_column=time_col,
                event_column=event_col,
                survival_time_unit=time_unit,
                event_type=event_type,
                reasoning=f"Regex fallback detected time column '{time_col}' and event column '{event_col}'",
                covariate_columns=covariate_cols,
            )

        logger.debug(f"Regex fallback found no survival data in {loaded_data.accession}")
        return None

    async def analyze_survival(
        self,
        loaded_data: LoadedGEOData,
        survival_time_col: Optional[str] = None,
        event_col: Optional[str] = None,
        time_unit: str = "days"
    ) -> Optional[SurvivalAnalysisResult]:
        """
        Perform survival analysis on a loaded dataset
        
        Args:
            loaded_data: Loaded GEO dataset with expression matrix and metadata
            survival_time_col: Column name for survival time (auto-detected if None)
            event_col: Column name for event status (auto-detected if None)
            time_unit: Unit of survival time
            
        Returns:
            SurvivalAnalysisResult or None if analysis fails
        """
        logger.info(f"Starting survival analysis for {loaded_data.accession}")
        log_memory_checkpoint("analyze_survival_start", context_id=loaded_data.accession)
        
        # Validate data
        if loaded_data.expression_matrix is None or loaded_data.expression_matrix.empty:
            logger.error(f"No expression data for {loaded_data.accession}")
            return None
        
        if loaded_data.sample_metadata is None or loaded_data.sample_metadata.empty:
            logger.error(f"No sample metadata for {loaded_data.accession}")
            return None
        
        # Auto-detect survival columns if not provided
        if survival_time_col is None or event_col is None:
            detection = await self.detect_survival_data(loaded_data)

            if detection is None or not detection.has_survival_data or \
               detection.survival_time_column is None or detection.event_column is None:
                # Try regex-based fallback before giving up
                logger.info(f"LLM detection failed for {loaded_data.accession}, trying regex fallback")
                detection = self.detect_survival_data_regex(loaded_data)

                if detection is None or not detection.has_survival_data or \
                   detection.survival_time_column is None or detection.event_column is None:
                    logger.warning(f"No survival data detected in {loaded_data.accession} (LLM + regex both failed)")
                    return None

            # Handle comma-separated column names from LLM (take the first one)
            survival_time_col = detection.survival_time_column
            if survival_time_col and ',' in survival_time_col:
                survival_time_col = survival_time_col.split(',')[0].strip()
                logger.debug(f"Multiple time columns detected, using first: {survival_time_col}")

            event_col = detection.event_column
            if event_col and ',' in event_col:
                event_col = event_col.split(',')[0].strip()
                logger.debug(f"Multiple event columns detected, using first: {event_col}")

            time_unit = detection.survival_time_unit
            event_type = detection.event_type
            covariate_columns = list(detection.covariate_columns) if detection.covariate_columns else []

            logger.info(f"Detected survival columns: time={survival_time_col}, event={event_col}")
        else:
            event_type = "death"
            covariate_columns = []
        
        # Extract survival data from metadata
        try:
            survival_df = self._extract_survival_data(
                loaded_data, survival_time_col, event_col
            )
        except ValueError as e:
            logger.error(f"Failed to extract survival data: {e}")
            return None
        
        if survival_df is None or len(survival_df) < self.min_samples_per_group * 2:
            logger.error(f"Insufficient samples with survival data: {len(survival_df) if survival_df is not None else 0}")
            return None
        
        logger.info(f"Extracted survival data for {len(survival_df)} samples")
        
        # Align expression matrix with survival data
        common_samples = list(set(loaded_data.expression_matrix.columns) & set(survival_df.index))
        
        if len(common_samples) < self.min_samples_per_group * 2:
            logger.error(f"Too few common samples: {len(common_samples)}")
            return None
        
        expression_matrix = loaded_data.expression_matrix[common_samples]
        survival_df = survival_df.loc[common_samples]
        log_memory_checkpoint("expression_matrix_sliced", context_id=loaded_data.accession)

        # Align metadata to common_samples for multivariate Cox (F13)
        metadata_aligned: Optional[pd.DataFrame] = None
        if covariate_columns and loaded_data.sample_metadata is not None:
            try:
                metadata_aligned = loaded_data.sample_metadata.loc[
                    loaded_data.sample_metadata.index.intersection(common_samples)
                ].reindex(common_samples)
            except Exception as e:
                logger.debug(f"Could not align metadata for multivariate Cox: {e}")

        logger.info(f"Analyzing {len(expression_matrix)} genes across {len(common_samples)} samples")

        # Perform survival analysis for each gene
        significant_genes = []
        n_analyzed = 0

        for gene_id in expression_matrix.index:
            try:
                gene_result = self._analyze_gene_survival(
                    gene_id=gene_id,
                    expression=expression_matrix.loc[gene_id],
                    survival_df=survival_df,
                    probe_to_gene=loaded_data.probe_to_gene_mapping,
                    metadata_df=metadata_aligned,
                    covariate_columns=covariate_columns if metadata_aligned is not None else None,
                )
                
                n_analyzed += 1
                
                if gene_result and gene_result.is_significant:
                    significant_genes.append(gene_result)
                    
            except Exception as e:
                logger.debug(f"Error analyzing gene {gene_id}: {e}")
                continue
        
        # Sort by Cox p-value
        significant_genes.sort(key=lambda x: x.cox_p_value)
        
        logger.info(f"Found {len(significant_genes)} significant genes out of {n_analyzed} analyzed")
        
        log_memory_checkpoint("analyze_survival_end", context_id=loaded_data.accession)
        return SurvivalAnalysisResult(
            accession=loaded_data.accession,
            title=loaded_data.title,
            platform=loaded_data.platform,
            n_samples=len(common_samples),
            n_genes_analyzed=n_analyzed,
            n_significant_genes=len(significant_genes),
            significant_genes=significant_genes,
            survival_time_unit=time_unit,
            event_type=event_type,
            analysis_method="Cox proportional hazards + Kaplan-Meier"
        )
    
    def _extract_survival_data(
        self,
        loaded_data: LoadedGEOData,
        time_col: str,
        event_col: str
    ) -> pd.DataFrame:
        """
        Extract and validate survival data from sample metadata
        
        Args:
            loaded_data: Loaded GEO dataset
            time_col: Column name for survival time
            event_col: Column name for event status
            
        Returns:
            DataFrame with 'time' and 'event' columns indexed by sample ID
        """
        # sample_metadata is already a DataFrame with samples as rows
        metadata_df = loaded_data.sample_metadata
        
        if time_col not in metadata_df.columns:
            raise ValueError(f"Time column '{time_col}' not found in metadata")
        if event_col not in metadata_df.columns:
            raise ValueError(f"Event column '{event_col}' not found in metadata")
        
        survival_df = pd.DataFrame({
            'time': self._parse_numeric_column(metadata_df[time_col]),
            'event': self._parse_event_column(metadata_df[event_col])
        })
        
        # Remove rows with missing data
        survival_df = survival_df.dropna()
        
        # Validate survival times are positive
        survival_df = survival_df[survival_df['time'] > 0]
        
        return survival_df
    
    def _parse_numeric_column(self, series: pd.Series) -> pd.Series:
        """
        Parse a column that may contain numeric values in various formats.
        Handles: plain numbers, "key: value" pairs (GEO characteristics format),
        and strings with embedded numbers.
        """
        # First try direct numeric conversion
        result = pd.to_numeric(series, errors='coerce')
        valid_count = result.notna().sum()

        # If most values converted, we're done
        if valid_count >= len(series) * 0.3:
            return result

        # Otherwise try extracting numbers from "key: value" style strings
        def extract_number(val):
            if pd.isna(val):
                return np.nan
            val_str = str(val).strip()
            # Try direct conversion first
            try:
                return float(val_str)
            except (ValueError, TypeError):
                pass
            # Extract number after colon (e.g., "os (months): 24.5")
            match = re.search(r':\s*([\d.]+)\s*$', val_str)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, TypeError):
                    pass
            # Extract trailing number (e.g., "survival_time 24")
            match = re.search(r'([\d.]+)\s*$', val_str)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, TypeError):
                    pass
            return np.nan

        return series.apply(extract_number)

    def _parse_event_column(self, event_series: pd.Series) -> pd.Series:
        """
        Parse event column to binary (0/1) format

        Handles various formats:
        - Binary: 0/1, True/False
        - Text: "dead"/"alive", "deceased"/"living", "event"/"censored"
        - GEO characteristics: "vital status: dead", "os event: 1"
        - Numeric: Any non-zero value as event
        """
        event_words = {'1', 'true', 'yes', 'dead', 'deceased', 'death', 'event', 'recurrence', 'relapsed'}
        censored_words = {'0', 'false', 'no', 'alive', 'living', 'censored', 'no_event', 'no event'}

        result = pd.Series(index=event_series.index, dtype=float)

        for idx, val in event_series.items():
            if pd.isna(val):
                result[idx] = np.nan
                continue

            val_str = str(val).lower().strip()

            # Extract value after colon for "key: value" format
            if ':' in val_str:
                val_str = val_str.split(':', 1)[1].strip()

            # Check for event indicators
            if val_str in event_words:
                result[idx] = 1.0
            elif val_str in censored_words:
                result[idx] = 0.0
            else:
                # Try numeric conversion
                try:
                    result[idx] = 1.0 if float(val_str) != 0 else 0.0
                except (ValueError, TypeError):
                    result[idx] = np.nan

        return result
    
    def _detect_covariate_columns(
        self,
        metadata_df: pd.DataFrame,
        exclude: Optional[set] = None,
    ) -> List[str]:
        """
        Identify clinical covariate columns (age, stage, grade, treatment) suitable
        for multivariate Cox regression.  Returns column names that have >70% non-null
        values and appear clinically relevant.
        """
        exclude = exclude or set()
        covariate_keywords = [
            'age', 'stage', 'grade', 'treatment', 'therapy', 'gender', 'sex',
            'tumor_size', 'size', 'node', 'metastasis', 'er_status', 'pr_status',
            'her2', 'histology', 'subtype', 'race', 'ethnicity', 'performance',
        ]
        found: List[str] = []
        for col in metadata_df.columns:
            if col in exclude:
                continue
            coverage = metadata_df[col].notna().mean()
            if coverage < 0.7:
                continue
            col_lower = col.lower()
            if any(kw in col_lower for kw in covariate_keywords):
                found.append(col)
        return found

    def _fit_multivariate_cox(
        self,
        expression_col: pd.Series,
        time_col: pd.Series,
        event_col: pd.Series,
        metadata_df: pd.DataFrame,
        covariate_candidates: List[str],
    ) -> Tuple[Optional[float], Optional[float], Optional[List[str]]]:
        """
        Fit a multivariate Cox model adjusting for clinical covariates.

        Returns:
            (adjusted_hr, adjusted_p, covariates_used) or (None, None, None) on failure.
        """
        try:
            # Filter covariates: must exist in metadata, have >70% non-null
            usable: List[str] = []
            for col in covariate_candidates:
                if col not in metadata_df.columns:
                    continue
                coverage = metadata_df[col].notna().mean()
                if coverage < 0.7:
                    continue
                usable.append(col)

            if not usable:
                return None, None, None

            # Build analysis dataframe
            df = pd.DataFrame({
                "expression": expression_col,
                "time": time_col,
                "event": event_col,
            })
            for col in usable:
                df[col] = metadata_df[col].values

            df = df.dropna()
            if len(df) < 20:
                return None, None, None

            # One-hot encode string/object columns
            cat_cols = [c for c in usable if df[c].dtype == object]
            if cat_cols:
                df = pd.get_dummies(df, columns=cat_cols, drop_first=True)
                usable = [c for c in df.columns if c not in ("expression", "time", "event")]

            cph = CoxPHFitter()
            cph.fit(df, duration_col="time", event_col="event")

            if "expression" not in cph.summary.index:
                return None, None, None

            expr_row = cph.summary.loc["expression"]
            adjusted_hr = float(np.exp(expr_row["coef"]))
            adjusted_p = float(expr_row["p"])
            return adjusted_hr, adjusted_p, usable

        except Exception as e:
            logger.debug(f"Multivariate Cox failed: {e}")
            return None, None, None

    def _analyze_gene_survival(
        self,
        gene_id: str,
        expression: pd.Series,
        survival_df: pd.DataFrame,
        probe_to_gene: Optional[Dict[str, str]] = None,
        metadata_df: Optional[pd.DataFrame] = None,
        covariate_columns: Optional[List[str]] = None,
    ) -> Optional[GeneSurvivalResult]:
        """
        Analyze survival association for a single gene
        
        Uses median expression to split samples into high/low groups,
        then performs log-rank test and Cox regression.
        """
        # Get gene symbol if available
        gene_symbol = probe_to_gene.get(gene_id) if probe_to_gene else None
        
        # Remove samples with missing expression
        valid_mask = ~expression.isna()
        expression = expression[valid_mask]
        survival_data = survival_df.loc[expression.index]
        
        if len(expression) < self.min_samples_per_group * 2:
            return None
        
        # Split by median expression
        median_expr = expression.median()
        high_expr_mask = expression >= median_expr
        
        n_high = high_expr_mask.sum()
        n_low = (~high_expr_mask).sum()
        
        if n_high < self.min_samples_per_group or n_low < self.min_samples_per_group:
            return None
        
        # Prepare data for analysis
        high_group = survival_data[high_expr_mask]
        low_group = survival_data[~high_expr_mask]
        
        # Log-rank test
        try:
            lr_result = logrank_test(
                high_group['time'], low_group['time'],
                event_observed_A=high_group['event'],
                event_observed_B=low_group['event']
            )
            log_rank_p = lr_result.p_value
        except Exception:
            log_rank_p = 1.0
        
        # Cox proportional hazards regression
        try:
            cox_df = survival_data.copy()
            cox_df['expression'] = expression
            
            cph = CoxPHFitter()
            cph.fit(cox_df, duration_col='time', event_col='event')
            
            cox_p = cph.summary.loc['expression', 'p']
            hazard_ratio = np.exp(cph.summary.loc['expression', 'coef'])
            hr_ci_lower = np.exp(cph.summary.loc['expression', 'coef lower 95%'])
            hr_ci_upper = np.exp(cph.summary.loc['expression', 'coef upper 95%'])
        except Exception:
            return None
        
        # Calculate median survival times and KM curves
        km_curve_high = None
        km_curve_low = None
        try:
            kmf = KaplanMeierFitter()
            
            # Helper function to sanitize values for JSON serialization
            def sanitize_value(val):
                """Convert NaN and inf to None for JSON serialization"""
                if val is None or pd.isna(val) or np.isinf(val):
                    return None
                return float(val)
            
            def sanitize_list(lst):
                """Sanitize a list of values for JSON serialization"""
                if lst is None:
                    return None
                return [sanitize_value(v) for v in lst]
            
            # Fit high expression group
            kmf.fit(high_group['time'], event_observed=high_group['event'])
            median_high = kmf.median_survival_time_
            
            # Extract KM curve data for high expression group
            km_curve_high = KMCurveData(
                times=sanitize_list(kmf.survival_function_.index.tolist()),
                survival_probabilities=sanitize_list(kmf.survival_function_['KM_estimate'].tolist()),
                ci_lower=sanitize_list(kmf.confidence_interval_['KM_estimate_lower_0.95'].tolist()) if hasattr(kmf, 'confidence_interval_') else None,
                ci_upper=sanitize_list(kmf.confidence_interval_['KM_estimate_upper_0.95'].tolist()) if hasattr(kmf, 'confidence_interval_') else None,
                n_samples=int(n_high),
                n_events=int(high_group['event'].sum())
            )
            
            # Fit low expression group
            kmf.fit(low_group['time'], event_observed=low_group['event'])
            median_low = kmf.median_survival_time_
            
            # Extract KM curve data for low expression group
            km_curve_low = KMCurveData(
                times=sanitize_list(kmf.survival_function_.index.tolist()),
                survival_probabilities=sanitize_list(kmf.survival_function_['KM_estimate'].tolist()),
                ci_lower=sanitize_list(kmf.confidence_interval_['KM_estimate_lower_0.95'].tolist()) if hasattr(kmf, 'confidence_interval_') else None,
                ci_upper=sanitize_list(kmf.confidence_interval_['KM_estimate_upper_0.95'].tolist()) if hasattr(kmf, 'confidence_interval_') else None,
                n_samples=int(n_low),
                n_events=int(low_group['event'].sum())
            )
        except Exception as e:
            logger.debug(f"Error calculating KM curves for {gene_id}: {e}")
            median_high = None
            median_low = None
        
        # Determine if significant
        is_significant = (
            cox_p < self.p_value_threshold and
            (hazard_ratio >= self.hazard_ratio_threshold or 
             hazard_ratio <= 1/self.hazard_ratio_threshold)
        )
        
        # Determine expression direction
        expression_direction = "high_risk" if hazard_ratio > 1 else "low_risk"
        
        # Convert infinity and NaN values to None for JSON serialization
        def safe_float(value):
            """Convert NaN and inf to None"""
            if value is None or pd.isna(value) or np.isinf(value):
                return None
            return float(value)
        
        # Multivariate Cox regression with clinical covariates (F13)
        adjusted_hr: Optional[float] = None
        adjusted_p: Optional[float] = None
        covariates_used: Optional[List[str]] = None
        if metadata_df is not None and covariate_columns:
            # Align metadata to the same samples as survival_df (after valid_mask filter)
            aligned_meta = metadata_df.loc[
                metadata_df.index.intersection(survival_data.index)
            ] if metadata_df.index.name == survival_data.index.name or set(metadata_df.index).issuperset(set(survival_data.index)) else None
            if aligned_meta is not None and len(aligned_meta) == len(survival_data):
                adjusted_hr, adjusted_p, covariates_used = self._fit_multivariate_cox(
                    expression_col=expression,
                    time_col=survival_data['time'],
                    event_col=survival_data['event'],
                    metadata_df=aligned_meta,
                    covariate_candidates=covariate_columns,
                )

        return GeneSurvivalResult(
            gene_id=gene_id,
            gene_symbol=gene_symbol,
            hazard_ratio=hazard_ratio,
            hazard_ratio_ci_lower=hr_ci_lower,
            hazard_ratio_ci_upper=hr_ci_upper,
            log_rank_p_value=log_rank_p,
            cox_p_value=cox_p,
            median_survival_high=safe_float(median_high),
            median_survival_low=safe_float(median_low),
            is_significant=is_significant,
            expression_direction=expression_direction,
            n_samples_high=n_high,
            n_samples_low=n_low,
            km_curve_high=km_curve_high,
            km_curve_low=km_curve_low,
            adjusted_hazard_ratio=safe_float(adjusted_hr),
            multivariate_cox_p=safe_float(adjusted_p),
            covariates_used=covariates_used,
        )
    
    def generate_kaplan_meier_data(
        self,
        loaded_data: LoadedGEOData,
        gene_id: str,
        survival_time_col: str,
        event_col: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate Kaplan-Meier curve data for a specific gene
        
        Returns data suitable for frontend visualization.
        """
        try:
            # sample_metadata is already a DataFrame with samples as rows
            metadata_df = loaded_data.sample_metadata
            expression = loaded_data.expression_matrix.loc[gene_id]
            
            # Extract survival data
            survival_df = pd.DataFrame({
                'time': pd.to_numeric(metadata_df[survival_time_col], errors='coerce'),
                'event': self._parse_event_column(metadata_df[event_col])
            })
            
            # Align data
            common_samples = list(set(expression.index) & set(survival_df.index))
            expression = expression[common_samples]
            survival_df = survival_df.loc[common_samples].dropna()
            expression = expression[survival_df.index]
            
            # Split by median
            median_expr = expression.median()
            high_mask = expression >= median_expr
            
            high_group = survival_df[high_mask]
            low_group = survival_df[~high_mask]
            
            # Fit KM curves
            kmf = KaplanMeierFitter()
            
            kmf.fit(high_group['time'], event_observed=high_group['event'])
            high_curve = {
                'times': kmf.survival_function_.index.tolist(),
                'survival_prob': kmf.survival_function_['KM_estimate'].tolist(),
                'ci_lower': kmf.confidence_interval_['KM_estimate_lower_0.95'].tolist(),
                'ci_upper': kmf.confidence_interval_['KM_estimate_upper_0.95'].tolist()
            }
            
            kmf.fit(low_group['time'], event_observed=low_group['event'])
            low_curve = {
                'times': kmf.survival_function_.index.tolist(),
                'survival_prob': kmf.survival_function_['KM_estimate'].tolist(),
                'ci_lower': kmf.confidence_interval_['KM_estimate_lower_0.95'].tolist(),
                'ci_upper': kmf.confidence_interval_['KM_estimate_upper_0.95'].tolist()
            }
            
            # Get gene symbol
            gene_symbol = loaded_data.probe_to_gene_mapping.get(gene_id, gene_id)
            
            return {
                'gene_id': gene_id,
                'gene_symbol': gene_symbol,
                'high_expression': high_curve,
                'low_expression': low_curve,
                'n_high': int(high_mask.sum()),
                'n_low': int((~high_mask).sum())
            }
            
        except Exception as e:
            logger.error(f"Failed to generate KM data for {gene_id}: {e}")
            return None


# Utility function for batch analysis
async def analyze_datasets_survival(
    datasets: List[LoadedGEOData],
    service: SurvivalAnalysisService
) -> List[SurvivalAnalysisResult]:
    """
    Analyze multiple datasets for survival associations
    
    Args:
        datasets: List of loaded GEO datasets
        service: SurvivalAnalysisService instance
        
    Returns:
        List of SurvivalAnalysisResult objects
    """
    results = []
    
    for dataset in datasets:
        try:
            result = await service.analyze_survival(dataset)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Failed survival analysis for {dataset.accession}: {e}")
            continue
    
    return results
