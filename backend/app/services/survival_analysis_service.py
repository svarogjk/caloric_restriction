"""
Survival Analysis Service
Performs survival analysis on GEO datasets to identify genes associated with lifespan/longevity
"""

import asyncio
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
from statsmodels.stats.multitest import multipletests
from pydantic_ai import Agent
from pydantic import BaseModel, Field

from app.config.logging_config import get_logger
from app.services.geo_loader_service import LoadedGEOData
from app.services.covariate_utils import select_usable_covariates
from app.utils.memory_tracker import track_memory, log_memory_checkpoint

logger = get_logger(__name__)
warnings.filterwarnings('ignore')

# GEO administrative columns that are never clinically relevant — excluded from LLM detection prompt
GEO_ADMIN_COLS = {
    'geo_accession', 'status', 'submission_date', 'last_update_date', 'type',
    'channel_count', 'source_name_ch1', 'organism_ch1', 'molecule_ch1',
    'extract_protocol_ch1', 'label_ch1', 'label_protocol_ch1', 'taxid_ch1',
    'hyb_protocol', 'scan_protocol', 'data_processing', 'platform_id',
    'contact_name', 'contact_email', 'contact_laboratory', 'contact_department',
    'contact_institute', 'contact_address', 'contact_city', 'contact_state',
    'contact_zip/postal_code', 'contact_country', 'supplementary_file', 'data_row_count',
}

# Try to import survival analysis libraries
try:
    from lifelines import KaplanMeierFitter, CoxPHFitter
    from lifelines.statistics import logrank_test, multivariate_logrank_test
    from lifelines.exceptions import ConvergenceError
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False
    ConvergenceError = Exception  # type: ignore[assignment,misc]
    logger.warning("lifelines not installed. Install with: pip install lifelines")

# Cox-fit failures we treat as "no result" rather than crashing the analysis.
_COX_FIT_ERRORS = (ConvergenceError, ValueError, KeyError, ZeroDivisionError, np.linalg.LinAlgError)

# Free-text values in a GEO treatment/arm column that denote the UNTREATED /
# control arm; everything else with a real treatment label is the treated arm.
_UNTREATED_TOKENS = {
    "none", "no", "untreated", "control", "placebo", "observation", "obs",
    "no treatment", "no therapy", "vehicle", "0", "false", "absent", "naive",
}

# Common salt-form suffixes stripped when matching a suggested drug name
# against a free-text GEO treatment-arm label (e.g. "doxorubicin hydrochloride").
_SALT_SUFFIXES = {
    "hydrochloride", "hcl", "sulfate", "sulphate", "sodium", "citrate",
    "mesylate", "tartrate", "acetate", "phosphate", "maleate", "besylate",
}


def _normalize_drug_name(name: str) -> str:
    """Casefold a drug name, strip punctuation and common salt-form suffixes."""
    text = re.sub(r"[^a-z0-9\s\-]", " ", name.strip().lower())
    tokens = [t for t in text.split() if t not in _SALT_SUFFIXES]
    return " ".join(tokens).strip()


def _drug_name_tokens(name: str) -> set:
    """Split a (possibly multi-drug combo) string into normalized single-drug
    tokens, e.g. "Nivolumab,Atezolizumab" -> {"nivolumab", "atezolizumab"}."""
    parts = re.split(r"[,/+&]| and ", name, flags=re.IGNORECASE)
    return {norm for p in parts if (norm := _normalize_drug_name(p))}


def _arm_label_matches_drug(arm_label: str, drug_name: str) -> bool:
    """Guard against attributing a detected treatment arm to a drug that is
    not actually named in the arm's free-text label.

    Required because `_binarize_treatment`'s top-2-category fallback can
    produce an arm from categories unrelated to any specific drug, and DGIdb/
    CIViC drug strings are messy (salt forms, multi-drug combos). A Tier-1
    cohort-comparison KM curve must never be attached to a drug suggestion
    without this guard passing — that would be a hallucinated attribution.
    """
    label_norm = _normalize_drug_name(arm_label)
    if not label_norm:
        return False
    return any(
        token and (token in label_norm or label_norm in token)
        for token in _drug_name_tokens(drug_name)
    )


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
    # Predictive (treatment-effect-modifying) biomarker results (F16b).
    # interaction_p_value is the p of the expression x treatment term in a Cox
    # model; a small value means the gene's survival association DIFFERS by
    # treatment arm — i.e. the gene is predictive, not merely prognostic.
    interaction_p_value: Optional[float] = None
    # Per-arm expression hazard ratios: [{name, hazard_ratio, ci_lower, ci_upper,
    # n_samples, n_events}, ...] — powers the per-arm forest in the UI.
    treatment_arms: Optional[List[Dict[str, Any]]] = None
    is_predictive: bool = False
    # Benjamini-Hochberg adjusted cox_p_value, corrected across every gene
    # tested in the dataset (not just the raw-significant subset). is_significant
    # is decided from this, not from the raw cox_p_value, once FDR correction runs.
    fdr_adjusted_p_value: Optional[float] = None


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


@dataclass
class _RiskSetIndex:
    """Risk-set bookkeeping shared by every gene in a dataset.

    Built once from (time, event) alone — identical for every gene, since
    only the covariate (expression) values differ — and reused by both the
    vectorized log-rank test and the vectorized Cox fit below.
    """

    order: np.ndarray            # sample positions sorted by time, descending
    events_sorted: np.ndarray    # event indicator reordered by `order`
    start_pos: np.ndarray        # first sorted-position of each event tie-group
    end_pos: np.ndarray          # last sorted-position of each event tie-group
    d: np.ndarray                # event count per tie-group (d_k)
    n_at_risk: np.ndarray        # total at-risk count per tie-group (n_k)
    max_tie: int                 # largest d_k, bounds the Efron correction loop


def _build_risk_set_index(times: np.ndarray, events: np.ndarray) -> Optional["_RiskSetIndex"]:
    """Sort samples by time (descending) and locate each tied event-time group.

    Returns None when there are no observed events at all (nothing to fit).
    """
    order = np.argsort(-times, kind="stable")
    times_sorted = times[order]
    events_sorted = events[order].astype(np.float64)

    n = len(times_sorted)
    is_new_group = np.empty(n, dtype=bool)
    is_new_group[0] = True
    if n > 1:
        is_new_group[1:] = times_sorted[1:] != times_sorted[:-1]
    group_id = np.cumsum(is_new_group) - 1
    n_groups = int(group_id[-1]) + 1

    group_first = np.searchsorted(group_id, np.arange(n_groups), side="left")
    group_last = np.searchsorted(group_id, np.arange(n_groups), side="right") - 1

    events_cum = np.concatenate([[0.0], np.cumsum(events_sorted)])
    d_per_group = events_cum[group_last + 1] - events_cum[group_first]
    n_per_group = (group_last + 1).astype(np.float64)

    event_groups = np.nonzero(d_per_group > 0)[0]
    if len(event_groups) == 0:
        return None

    return _RiskSetIndex(
        order=order,
        events_sorted=events_sorted,
        start_pos=group_first[event_groups],
        end_pos=group_last[event_groups],
        d=d_per_group[event_groups],
        n_at_risk=n_per_group[event_groups],
        max_tie=int(d_per_group[event_groups].max()),
    )


def _segment_sums(values: np.ndarray, idx: "_RiskSetIndex") -> np.ndarray:
    """Sum `values` (n_genes, n_samples), already event-masked, within each
    tie group [start_pos, end_pos] — via a zero-padded cumulative sum."""
    padded = np.concatenate(
        [np.zeros((values.shape[0], 1)), np.cumsum(values, axis=1)], axis=1
    )
    return padded[:, idx.end_pos + 1] - padded[:, idx.start_pos]


def _vectorized_logrank_p(high_mask_sorted: np.ndarray, idx: "_RiskSetIndex") -> np.ndarray:
    """Two-group (Mantel-Haenszel) log-rank test p-value for every gene at once.

    `high_mask_sorted` is (n_genes, n_samples) boolean, already reordered to
    match `idx.order`. Matches `lifelines.statistics.logrank_test` (no
    continuity correction — the same default the scalar per-gene path uses).
    """
    high = high_mask_sorted.astype(np.float64)
    n_high_k = np.cumsum(high, axis=1)[:, idx.end_pos]

    high_event = high * idx.events_sorted[None, :]
    d_high_k = _segment_sums(high_event, idx)

    n_k = idx.n_at_risk[None, :]
    d_k = idx.d[None, :]

    p_high = n_high_k / n_k
    expected_high = d_k * p_high
    denom = np.where(n_k > 1, n_k - 1, 1.0)
    variance = d_k * p_high * (1 - p_high) * (n_k - d_k) / denom
    variance = np.where(n_k > 1, variance, 0.0)

    o_minus_e = np.sum(d_high_k - expected_high, axis=1)
    total_variance = np.sum(variance, axis=1)

    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(total_variance > 0, o_minus_e / np.sqrt(total_variance), np.nan)

    return stats.chi2.sf(z ** 2, df=1)


def _vectorized_cox_fit(
    X_sorted: np.ndarray,
    idx: "_RiskSetIndex",
    max_iter: int = 25,
    tol: float = 1e-6,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Univariate Cox proportional hazards fit (Efron ties) for every gene at
    once, via vectorized Newton-Raphson on the partial log-likelihood.

    `X_sorted` is (n_genes, n_samples), covariate (expression) values
    reordered to match `idx.order`. Mirrors `lifelines.CoxPHFitter` for the
    single-covariate case (same Efron score/information formulas, same
    Wald-based inference), but solves every gene's independent 1-parameter
    optimization simultaneously instead of one `.fit()` call per gene.

    Returns (beta, se, converged). Genes that fail to converge (numerical
    overflow, non-positive information, runaway coefficient) come back with
    `converged=False` so the caller can re-run just those through the exact
    `lifelines`-backed scalar path rather than trusting an unstable fit.
    """
    n_genes, _n_samples = X_sorted.shape
    events_row = idx.events_sorted[None, :]
    sum_x_k = _segment_sums(events_row * X_sorted, idx)  # constant across iterations

    beta = np.zeros(n_genes)
    delta = np.full(n_genes, np.nan)
    info_final = np.zeros(n_genes)

    for _ in range(max_iter):
        with np.errstate(over="ignore", invalid="ignore"):
            w = np.exp(beta[:, None] * X_sorted)
        xw = X_sorted * w
        x2w = X_sorted ** 2 * w

        S0_k = np.cumsum(w, axis=1)[:, idx.end_pos]
        S1_k = np.cumsum(xw, axis=1)[:, idx.end_pos]
        S2_k = np.cumsum(x2w, axis=1)[:, idx.end_pos]

        s0_k = _segment_sums(events_row * w, idx)
        s1_k = _segment_sums(events_row * xw, idx)
        s2_k = _segment_sums(events_row * x2w, idx)

        score = sum_x_k.sum(axis=1).copy()
        info = np.zeros(n_genes)

        for l in range(idx.max_tie):
            valid = idx.d > l
            if not valid.any():
                continue
            frac = np.where(valid, l / np.where(idx.d > 0, idx.d, 1.0), 0.0)[None, :]
            denom = np.where(valid[None, :], S0_k - frac * s0_k, 1.0)
            num1 = S1_k - frac * s1_k
            num2 = S2_k - frac * s2_k
            with np.errstate(invalid="ignore", divide="ignore"):
                term1 = num1 / denom
                term2 = num2 / denom - term1 ** 2
            mask = valid[None, :]
            score -= np.sum(np.where(mask, term1, 0.0), axis=1)
            info += np.sum(np.where(mask, term2, 0.0), axis=1)

        with np.errstate(invalid="ignore", divide="ignore"):
            delta = np.where(info > 0, score / info, np.nan)
        valid_step = np.isfinite(delta)
        beta = np.where(valid_step, beta + delta, beta)
        info_final = info

        max_delta = np.max(np.abs(delta[valid_step])) if valid_step.any() else 0.0
        if max_delta < tol:
            break

    se = np.full(n_genes, np.nan)
    positive_info = info_final > 0
    se[positive_info] = 1.0 / np.sqrt(info_final[positive_info])

    converged = (
        np.isfinite(beta)
        & np.isfinite(se)
        & positive_info
        & (np.abs(np.where(np.isfinite(delta), delta, np.inf)) < tol)
        & (np.abs(beta) < 50)  # runaway-coefficient guard: e^50 is not a real hazard ratio
    )

    return beta, se, converged


class SurvivalAnalysisService:
    """
    Service for performing survival analysis on gene expression data

    Identifies genes whose expression levels are associated with survival outcomes
    using Kaplan-Meier analysis and Cox proportional hazards regression.
    """
    
    def __init__(
        self,
        p_value_threshold: float = 0.05,
        hazard_ratio_upper: float = 1.2,
        hazard_ratio_lower: float = 0.8,
        min_samples_per_group: int = 5,
        model: str = "mistral"
    ):
        """
        Initialize survival analysis service

        Args:
            p_value_threshold: Significance threshold for Cox regression p-value
            hazard_ratio_upper: A gene is significant if HR >= this (risk-associated)
            hazard_ratio_lower: ...or HR <= this (protective-associated). Not required
                to be the reciprocal of hazard_ratio_upper — set independently.
            min_samples_per_group: Minimum samples required per expression group
            model: LLM model for survival data detection
        """
        if not LIFELINES_AVAILABLE:
            raise ImportError("lifelines library required for survival analysis. "
                            "Install with: pip install lifelines")

        self.p_value_threshold = p_value_threshold
        self.hazard_ratio_upper = hazard_ratio_upper
        self.hazard_ratio_lower = hazard_ratio_lower
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
        clinical_cols = [c for c in metadata_df.columns if c not in GEO_ADMIN_COLS]
        columns_info = []
        for col in clinical_cols[:60]:
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

    async def detect_survival_columns(
        self,
        loaded_data: LoadedGEOData
    ) -> Optional[SurvivalDataDetectionResponse]:
        """LLM detection first, regex fallback.

        Shared by ``analyze_survival`` and the signature builder so both resolve
        the same survival columns (the regex-only path misses non-standard names
        like ``drfi.time``, ``t.dmfs``/``e.dmfs`` or hyphenated ``follow-up_time``).
        """
        detection = await self.detect_survival_data(loaded_data)
        if detection is None or not detection.has_survival_data \
           or detection.survival_time_column is None or detection.event_column is None:
            logger.info(f"LLM detection failed for {loaded_data.accession}, trying regex fallback")
            detection = self.detect_survival_data_regex(loaded_data)

        if detection is None or not detection.has_survival_data \
           or detection.survival_time_column is None or detection.event_column is None:
            return None
        return detection

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
            # os_(months)_since_* style: any non-alpha bridge between endpoint and unit
            re.compile(r'(?:overall[_\s]?survival|os|rfs|dfs|pfs)[^a-z\d]*(?:months?|days?|years?)', re.I),
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
            # ose / rfse / dfse — common GEO abbreviations for OS/RFS event
            re.compile(r'^(?:os|rfs|dfs|pfs|efs|dss)e$', re.I),
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
            detection = await self.detect_survival_columns(loaded_data)

            if detection is None:
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

        # Collapse multiple probes mapping to the same gene (mean expression)
        # before per-gene analysis. Without this, a gene measured by several
        # probes on the array gets Cox-fit once per probe instead of once,
        # multiplying runtime and producing multiple independent "significant
        # gene" entries downstream that collide (and get discarded) when
        # results are aggregated across datasets by gene symbol.
        probe_to_gene = loaded_data.probe_to_gene_mapping
        if probe_to_gene:
            genes_before_aggregation = len(expression_matrix)
            expression_matrix, probe_to_gene = self._aggregate_probes_to_genes(
                expression_matrix, probe_to_gene
            )
            if len(expression_matrix) != genes_before_aggregation:
                logger.info(
                    f"Aggregated {genes_before_aggregation} probes -> "
                    f"{len(expression_matrix)} genes (mean expression) for {loaded_data.accession}"
                )

        # Align metadata to common_samples for multivariate Cox (F13)
        metadata_aligned: Optional[pd.DataFrame] = None
        if covariate_columns and loaded_data.sample_metadata is not None:
            try:
                metadata_aligned = loaded_data.sample_metadata.loc[
                    loaded_data.sample_metadata.index.intersection(common_samples)
                ].reindex(common_samples)
            except Exception as e:
                logger.debug(f"Could not align metadata for multivariate Cox: {e}")

        # Detect a treatment/arm column for the predictive interaction test (F16b).
        # Independent of covariate detection — the LLM may not flag treatment as a
        # confounder, but we still want it as the effect-modifier axis.
        treatment_binary: Optional[pd.Series] = None
        treatment_arm_names: Optional[Dict[int, str]] = None
        if loaded_data.sample_metadata is not None:
            try:
                meta_for_tx = loaded_data.sample_metadata.loc[
                    loaded_data.sample_metadata.index.intersection(common_samples)
                ].reindex(common_samples)
                tx_col = self._detect_treatment_column(
                    meta_for_tx, exclude={survival_time_col, event_col}
                )
                if tx_col is not None:
                    binarized = self._binarize_treatment(meta_for_tx[tx_col])
                    if binarized is not None:
                        treatment_binary, treatment_arm_names = binarized
                        logger.info(
                            f"Predictive analysis enabled for {loaded_data.accession}: "
                            f"treatment column '{tx_col}' -> arms "
                            f"{list(treatment_arm_names.values())}"
                        )
            except (KeyError, ValueError) as e:
                logger.debug(f"Treatment detection failed for {loaded_data.accession}: {e}")

        logger.info(f"Analyzing {len(expression_matrix)} genes across {len(common_samples)} samples (filtered={len(loaded_data.expression_matrix)} total genes before sample filtering)")

        # Perform survival analysis for each gene. This is CPU-bound (per-gene
        # CoxPHFitter fits), so it's run off the event loop thread — otherwise
        # it monopolizes the single asyncio event loop and stalls every other
        # concurrent request (e.g. a second browser tab) for the duration.
        significant_genes, n_analyzed = await asyncio.to_thread(
            self._analyze_all_genes,
            expression_matrix,
            survival_df,
            probe_to_gene,
            metadata_aligned,
            covariate_columns if metadata_aligned is not None else None,
            treatment_binary,
            treatment_arm_names,
        )

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

    @staticmethod
    def _aggregate_probes_to_genes(
        expression_matrix: pd.DataFrame,
        probe_to_gene: Dict[str, str],
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """Collapse multiple probes mapping to the same gene symbol into a
        single row (mean expression, matching the aggregation pattern in
        signature_service._reduce_cohort_to_candidates). Probes without a
        mapped gene symbol are kept as-is, indexed by their original probe ID.
        """
        rows: Dict[str, List[str]] = {}
        unmapped: List[str] = []
        for probe in expression_matrix.index:
            symbol = probe_to_gene.get(probe)
            if symbol:
                rows.setdefault(symbol.upper().strip(), []).append(probe)
            else:
                unmapped.append(probe)

        if not rows:
            return expression_matrix, probe_to_gene

        gene_matrix = pd.DataFrame(
            {sym: expression_matrix.loc[probes].mean(axis=0) for sym, probes in rows.items()}
        ).T

        combined = (
            pd.concat([gene_matrix, expression_matrix.loc[unmapped]])
            if unmapped else gene_matrix
        )
        identity_mapping = {sym: sym for sym in rows}
        return combined, identity_mapping

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

    def _detect_treatment_column(
        self,
        metadata_df: pd.DataFrame,
        exclude: Optional[set] = None,
    ) -> Optional[str]:
        """Identify a treatment/therapy/arm column suitable for a predictive
        (treatment-effect-modifying) interaction test.

        Returns the column name with the best coverage that binarizes into two
        adequately-sized arms, or None. Mirrors `_detect_covariate_columns` but
        is narrowed to treatment-exposure terms (not generic confounders).
        """
        exclude = exclude or set()
        treatment_keywords = [
            'treatment', 'therapy', 'arm', 'regimen', 'chemo', 'chemotherapy',
            'adjuvant', 'drug', 'agent', 'tamoxifen', 'endocrine', 'radiation',
            'radiotherapy', 'targeted', 'immunotherapy',
        ]
        best_col: Optional[str] = None
        best_coverage = 0.0
        for col in metadata_df.columns:
            if col in exclude:
                continue
            coverage = metadata_df[col].notna().mean()
            if coverage < 0.7:
                continue
            if not any(kw in col.lower() for kw in treatment_keywords):
                continue
            # Must binarize into two adequately-sized arms.
            if self._binarize_treatment(metadata_df[col]) is None:
                continue
            if coverage > best_coverage:
                best_coverage = coverage
                best_col = col
        return best_col

    def _binarize_treatment(
        self,
        series: pd.Series,
    ) -> Optional[Tuple[pd.Series, Dict[int, str]]]:
        """Reduce a free-text GEO treatment column to a 0/1 arm indicator.

        Strategy: map values whose text matches an untreated/control token to 0
        and everything else (a real treatment label) to 1. If that split is too
        lopsided, fall back to the two most frequent distinct categories.

        Returns (binary_series_indexed_like_input, {0: nameA, 1: nameB}) or None
        when two arms of at least `min_samples_per_group` each cannot be formed.
        """
        def _norm(val) -> Optional[str]:
            if pd.isna(val):
                return None
            text = str(val).strip().lower()
            if ':' in text:
                text = text.split(':', 1)[1].strip()
            return text or None

        normalized = series.map(_norm)
        non_null = normalized.dropna()
        if non_null.nunique() < 2:
            return None

        min_n = self.min_samples_per_group

        # Primary: treated vs untreated by token.
        treated_mask = ~non_null.isin(_UNTREATED_TOKENS)
        n_treated = int(treated_mask.sum())
        n_untreated = int((~treated_mask).sum())
        if n_treated >= min_n and n_untreated >= min_n:
            binary = pd.Series(index=series.index, dtype="float")
            binary.loc[non_null.index[treated_mask.values]] = 1.0
            binary.loc[non_null.index[(~treated_mask).values]] = 0.0
            return binary, {0: "Untreated/control", 1: "Treated"}

        # Fallback: two most frequent distinct categories.
        top2 = non_null.value_counts().head(2)
        if len(top2) < 2 or top2.iloc[1] < min_n:
            return None
        (label_one, _), (label_zero, _) = top2.items()
        binary = pd.Series(index=series.index, dtype="float")
        in_one = non_null == label_one
        in_zero = non_null == label_zero
        binary.loc[non_null.index[in_one.values]] = 1.0
        binary.loc[non_null.index[in_zero.values]] = 0.0
        return binary, {0: label_zero.title(), 1: label_one.title()}

    def _fit_interaction_cox(
        self,
        expression_col: pd.Series,
        time_col: pd.Series,
        event_col: pd.Series,
        treatment_binary: pd.Series,
        arm_names: Dict[int, str],
    ) -> Optional[Tuple[float, List[Dict[str, Any]]]]:
        """Predictive-biomarker test: fit a Cox model with an
        ``expression x treatment`` interaction term and per-arm expression HRs.

        Returns (interaction_p_value, treatment_arms) where treatment_arms lists
        each arm's expression hazard ratio + 95% CI, or None when the model
        cannot be fit (too few rows/events per arm, non-convergence).
        """
        df = pd.DataFrame({
            "expression": expression_col,
            "treatment": treatment_binary,
            "time": time_col,
            "event": event_col,
        }).dropna()
        if len(df) < 20:
            return None

        # Require both arms to carry enough events for a stable per-arm HR.
        per_arm: List[Dict[str, Any]] = []
        for arm_value in (0, 1):
            sub = df[df["treatment"] == arm_value]
            n = len(sub)
            n_events = int(sub["event"].sum())
            if n < self.min_samples_per_group or n_events < 10:
                return None
            try:
                cph = CoxPHFitter()
                cph.fit(sub[["expression", "time", "event"]], duration_col="time", event_col="event")
                row = cph.summary.loc["expression"]
                per_arm.append({
                    "name": arm_names.get(arm_value, f"arm {arm_value}"),
                    "hazard_ratio": float(np.exp(row["coef"])),
                    "ci_lower": float(np.exp(row["coef lower 95%"])),
                    "ci_upper": float(np.exp(row["coef upper 95%"])),
                    "n_samples": n,
                    "n_events": n_events,
                })
            except _COX_FIT_ERRORS as e:
                logger.debug("Per-arm Cox failed: %s", e)
                return None

        # Interaction term: a significant expr x treatment coefficient means the
        # gene's effect on survival is treatment-dependent (predictive).
        try:
            inter = df.copy()
            inter["expr_x_treat"] = inter["expression"] * inter["treatment"]
            cph = CoxPHFitter()
            cph.fit(
                inter[["expression", "treatment", "expr_x_treat", "time", "event"]],
                duration_col="time",
                event_col="event",
            )
            if "expr_x_treat" not in cph.summary.index:
                return None
            interaction_p = float(cph.summary.loc["expr_x_treat", "p"])
        except _COX_FIT_ERRORS as e:
            logger.debug("Interaction Cox failed: %s", e)
            return None

        if not np.isfinite(interaction_p):
            return None
        return interaction_p, per_arm

    def _fit_treatment_arm_km(
        self,
        time_col: pd.Series,
        event_col: pd.Series,
        treatment_binary: pd.Series,
        arm_names: Dict[int, str],
    ) -> Optional[List[Dict[str, Any]]]:
        """Descriptive per-arm Kaplan-Meier curves (treated vs untreated/control),
        independent of any gene expression or interaction test.

        Powers the "Treatments to consider" Tier-1 cohort-comparison KM chart:
        purely observational survival-by-arm, not a predictiveness claim (that
        is `_fit_interaction_cox`'s job). Uses the same sample/event floors as
        `_fit_interaction_cox` for consistency. Returns None when either arm
        is too small or a fit fails — never a partial/fabricated curve.
        """
        df = pd.DataFrame({
            "treatment": treatment_binary, "time": time_col, "event": event_col,
        }).dropna()
        if len(df) < 20:
            return None

        def sanitize_value(val):
            if val is None or pd.isna(val) or np.isinf(val):
                return None
            return float(val)

        def sanitize_list(lst):
            return [sanitize_value(v) for v in lst] if lst is not None else None

        arms: List[Dict[str, Any]] = []
        for arm_value in (0, 1):
            sub = df[df["treatment"] == arm_value]
            n = len(sub)
            n_events = int(sub["event"].sum())
            if n < self.min_samples_per_group or n_events < 10:
                return None
            try:
                kmf = KaplanMeierFitter()
                kmf.fit(sub["time"], event_observed=sub["event"])
                km_curve = {
                    "times": sanitize_list(kmf.survival_function_.index.tolist()),
                    "survival_probabilities": sanitize_list(
                        kmf.survival_function_["KM_estimate"].tolist()
                    ),
                    "ci_lower": sanitize_list(
                        kmf.confidence_interval_["KM_estimate_lower_0.95"].tolist()
                    ) if hasattr(kmf, "confidence_interval_") else None,
                    "ci_upper": sanitize_list(
                        kmf.confidence_interval_["KM_estimate_upper_0.95"].tolist()
                    ) if hasattr(kmf, "confidence_interval_") else None,
                    "n_samples": n,
                    "n_events": n_events,
                }
            except _COX_FIT_ERRORS as e:
                logger.debug("Per-arm KM fit failed: %s", e)
                return None
            arms.append({
                "name": arm_names.get(arm_value, f"arm {arm_value}"),
                "n_samples": n,
                "n_events": n_events,
                "km_curve": km_curve,
            })
        return arms

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
            usable = select_usable_covariates(metadata_df, covariate_candidates)

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

    def _analyze_all_genes(
        self,
        expression_matrix: pd.DataFrame,
        survival_df: pd.DataFrame,
        probe_to_gene: Optional[Dict[str, str]],
        metadata_aligned: Optional[pd.DataFrame],
        covariate_columns: Optional[List[str]],
        treatment_binary: Optional[pd.Series],
        treatment_arm_names: Optional[Dict[int, str]],
    ) -> Tuple[List[GeneSurvivalResult], int]:
        """Synchronous per-gene survival analysis, meant to be run via asyncio.to_thread.

        Tries the vectorized fast path (log-rank + Cox for every gene in one
        batch of numpy ops) first; falls back to the exact per-gene
        `lifelines` loop — unchanged — for any gene it can't safely fast-path,
        or for the whole dataset if the vectorized path hits anything
        unexpected.

        Significance is decided from the Benjamini-Hochberg FDR-adjusted
        p-value across every gene tested in the dataset, not the raw Cox
        p-value — per rules/survival-analysis.md ("Apply FDR correction when
        analyzing many genes"). Without this, testing tens of thousands of
        genes at a raw p<0.05 threshold produces thousands of false positives
        by chance alone.
        """
        try:
            candidates, n_analyzed, raw_pvalues = self._analyze_all_genes_vectorized(
                expression_matrix,
                survival_df,
                probe_to_gene,
                metadata_aligned,
                covariate_columns,
                treatment_binary,
                treatment_arm_names,
            )
        except Exception as e:
            logger.warning(f"Vectorized gene analysis failed ({e}); falling back to per-gene loop")
            candidates, n_analyzed, raw_pvalues = self._analyze_all_genes_scalar(
                expression_matrix,
                survival_df,
                probe_to_gene,
                metadata_aligned,
                covariate_columns,
                treatment_binary,
                treatment_arm_names,
            )

        significant_genes = self._apply_fdr_correction(candidates, raw_pvalues)
        return significant_genes, n_analyzed

    def _apply_fdr_correction(
        self,
        candidates: List[GeneSurvivalResult],
        raw_pvalues: Dict[str, float],
    ) -> List[GeneSurvivalResult]:
        """Re-decide significance via Benjamini-Hochberg FDR correction across
        every gene actually tested (`raw_pvalues`), not just the raw-significant
        subset (`candidates`).

        `candidates` is a safe superset to re-filter without building full
        results (KM curves, multivariate/interaction Cox) for the whole
        genome: FDR-adjusted p-values are never smaller than the raw p-value,
        so a gene that didn't clear the raw threshold can never clear the
        FDR-corrected one either.
        """
        if not raw_pvalues:
            return []

        gene_ids = list(raw_pvalues.keys())
        pvals = list(raw_pvalues.values())
        try:
            reject, adj_p, _, _ = multipletests(pvals, method='fdr_bh', alpha=self.p_value_threshold)
            adj_p_by_gene = dict(zip(gene_ids, adj_p))
            reject_by_gene = dict(zip(gene_ids, reject))
        except ValueError as e:
            logger.warning(f"FDR correction failed ({e}); falling back to raw p-value threshold")
            adj_p_by_gene = dict(zip(gene_ids, pvals))
            reject_by_gene = {gid: p < self.p_value_threshold for gid, p in raw_pvalues.items()}

        significant_genes = []
        for gene_result in candidates:
            adj_p = adj_p_by_gene.get(gene_result.gene_id)
            if adj_p is None:
                continue
            gene_result.fdr_adjusted_p_value = float(adj_p)
            gene_result.is_significant = bool(reject_by_gene.get(gene_result.gene_id, False)) and (
                gene_result.hazard_ratio >= self.hazard_ratio_upper
                or gene_result.hazard_ratio <= self.hazard_ratio_lower
            )
            if gene_result.is_significant:
                significant_genes.append(gene_result)

        significant_genes.sort(key=lambda x: x.cox_p_value)
        return significant_genes

    def _analyze_all_genes_vectorized(
        self,
        expression_matrix: pd.DataFrame,
        survival_df: pd.DataFrame,
        probe_to_gene: Optional[Dict[str, str]],
        metadata_aligned: Optional[pd.DataFrame],
        covariate_columns: Optional[List[str]],
        treatment_binary: Optional[pd.Series],
        treatment_arm_names: Optional[Dict[int, str]],
    ) -> Tuple[List[GeneSurvivalResult], int, Dict[str, float]]:
        """Fast path: log-rank + univariate Cox for every gene at once.

        Genes with any missing expression value fall back to the scalar path
        immediately (their risk sets differ from every other gene's, so they
        can't share the batched computation). Among the rest, any gene whose
        vectorized Cox fit doesn't cleanly converge also falls back to the
        scalar path rather than trusting an unstable result. Only genes that
        clear the significance bar get the expensive KM-curve /
        multivariate / interaction extras computed at all — those were
        previously computed for every gene regardless of significance, even
        though only significant genes are ever returned.

        Also returns `raw_pvalues`, the uncorrected Cox p-value for every gene
        that got a valid fit (significant or not) — the `_analyze_all_genes`
        caller needs the full test set to apply FDR correction.
        """
        gene_ids = expression_matrix.index.to_numpy()
        X_all = expression_matrix.to_numpy(dtype=np.float64)
        n_genes, n_samples = X_all.shape

        significant_genes: List[GeneSurvivalResult] = []
        raw_pvalues: Dict[str, float] = {}
        n_analyzed = 0

        has_nan = np.isnan(X_all).any(axis=1)
        dirty_positions = np.nonzero(has_nan)[0]
        clean_positions = np.nonzero(~has_nan)[0]

        if len(dirty_positions) > 0:
            dirty_genes, dirty_n, dirty_pvalues = self._analyze_all_genes_scalar(
                expression_matrix.iloc[dirty_positions],
                survival_df, probe_to_gene, metadata_aligned,
                covariate_columns, treatment_binary, treatment_arm_names,
            )
            significant_genes.extend(dirty_genes)
            raw_pvalues.update(dirty_pvalues)
            n_analyzed += dirty_n

        if len(clean_positions) == 0:
            significant_genes.sort(key=lambda x: x.cox_p_value)
            return significant_genes, n_analyzed, raw_pvalues

        times = survival_df['time'].to_numpy(dtype=np.float64)
        events = survival_df['event'].to_numpy(dtype=np.float64)
        risk_index = _build_risk_set_index(times, events)

        X_clean = X_all[clean_positions]
        clean_gene_ids = gene_ids[clean_positions]

        if risk_index is None:
            # No observed events at all — nothing to fit for any gene.
            n_analyzed += len(clean_positions)
            significant_genes.sort(key=lambda x: x.cox_p_value)
            return significant_genes, n_analyzed, raw_pvalues

        median_per_gene = np.median(X_clean, axis=1)
        high_mask = X_clean >= median_per_gene[:, None]
        n_high = high_mask.sum(axis=1)
        n_low = n_samples - n_high
        valid_split = (
            (n_samples >= self.min_samples_per_group * 2)
            & (n_high >= self.min_samples_per_group)
            & (n_low >= self.min_samples_per_group)
        )

        # Every clean gene is "attempted" here, matching the scalar loop's
        # counting: n_analyzed increments whenever the per-gene call doesn't
        # raise, regardless of whether it found a valid split.
        n_analyzed += len(clean_positions)

        X_sorted = X_clean[:, risk_index.order]
        beta, se, cox_converged = _vectorized_cox_fit(X_sorted, risk_index)

        high_mask_sorted = high_mask[:, risk_index.order]
        log_rank_p = _vectorized_logrank_p(high_mask_sorted, risk_index)

        needs_fallback = valid_split & ~cox_converged
        if needs_fallback.any():
            fallback_positions = np.nonzero(needs_fallback)[0]
            fallback_genes, _fallback_n, fallback_pvalues = self._analyze_all_genes_scalar(
                expression_matrix.loc[clean_gene_ids[fallback_positions]],
                survival_df, probe_to_gene, metadata_aligned,
                covariate_columns, treatment_binary, treatment_arm_names,
            )
            # These genes are already counted in n_analyzed above. The scalar
            # p-values are authoritative here — the vectorized cox_p for
            # these positions comes from a fit that didn't cleanly converge.
            significant_genes.extend(fallback_genes)
            raw_pvalues.update(fallback_pvalues)

        use_fast = valid_split & cox_converged
        hazard_ratio = np.exp(beta)
        with np.errstate(invalid="ignore", divide="ignore"):
            z = np.where(se > 0, beta / se, np.nan)
        cox_p = stats.chi2.sf(z ** 2, df=1)
        z_crit = stats.norm.ppf(0.975)
        hr_ci_lower = np.exp(beta - z_crit * se)
        hr_ci_upper = np.exp(beta + z_crit * se)

        for pos in np.nonzero(use_fast)[0]:
            raw_pvalues[clean_gene_ids[pos]] = float(cox_p[pos])

        is_significant = (
            use_fast
            & (cox_p < self.p_value_threshold)
            & ((hazard_ratio >= self.hazard_ratio_upper) | (hazard_ratio <= self.hazard_ratio_lower))
        )

        survival_time = survival_df['time']
        survival_event = survival_df['event']
        for pos in np.nonzero(is_significant)[0]:
            gene_id = clean_gene_ids[pos]
            high = high_mask[pos]
            result = self._finalize_gene_result(
                gene_id=gene_id,
                gene_symbol=probe_to_gene.get(gene_id) if probe_to_gene else None,
                expression=pd.Series(X_clean[pos], index=expression_matrix.columns),
                survival_data=survival_df,
                high_group=survival_df[high],
                low_group=survival_df[~high],
                n_high=int(n_high[pos]),
                n_low=int(n_low[pos]),
                hazard_ratio=float(hazard_ratio[pos]),
                hr_ci_lower=float(hr_ci_lower[pos]),
                hr_ci_upper=float(hr_ci_upper[pos]),
                cox_p=float(cox_p[pos]),
                log_rank_p=float(log_rank_p[pos]),
                metadata_df=metadata_aligned,
                covariate_columns=covariate_columns,
                treatment_binary=treatment_binary,
                treatment_arm_names=treatment_arm_names,
            )
            if result is not None:
                significant_genes.append(result)

        significant_genes.sort(key=lambda x: x.cox_p_value)
        return significant_genes, n_analyzed, raw_pvalues

    def _finalize_gene_result(
        self,
        gene_id: str,
        gene_symbol: Optional[str],
        expression: pd.Series,
        survival_data: pd.DataFrame,
        high_group: pd.DataFrame,
        low_group: pd.DataFrame,
        n_high: int,
        n_low: int,
        hazard_ratio: float,
        hr_ci_lower: float,
        hr_ci_upper: float,
        cox_p: float,
        log_rank_p: float,
        metadata_df: Optional[pd.DataFrame],
        covariate_columns: Optional[List[str]],
        treatment_binary: Optional[pd.Series],
        treatment_arm_names: Optional[Dict[int, str]],
    ) -> GeneSurvivalResult:
        """Build the full result for a gene already known to be significant
        from the vectorized log-rank/Cox pass: KM curves, multivariate Cox
        (F13), and the treatment-interaction predictive test (F16b).

        This is the same work `_analyze_gene_survival` does after its own Cox
        fit — duplicated rather than shared so the existing, directly-tested
        scalar path stays untouched. Only called for genes that clear the
        significance bar, since non-significant genes never reach the caller.
        """
        km_curve_high = None
        km_curve_low = None
        median_high = None
        median_low = None
        try:
            kmf = KaplanMeierFitter()

            def sanitize_value(val):
                if val is None or pd.isna(val) or np.isinf(val):
                    return None
                return float(val)

            def sanitize_list(lst):
                if lst is None:
                    return None
                return [sanitize_value(v) for v in lst]

            kmf.fit(high_group['time'], event_observed=high_group['event'])
            median_high = kmf.median_survival_time_
            km_curve_high = KMCurveData(
                times=sanitize_list(kmf.survival_function_.index.tolist()),
                survival_probabilities=sanitize_list(kmf.survival_function_['KM_estimate'].tolist()),
                ci_lower=sanitize_list(kmf.confidence_interval_['KM_estimate_lower_0.95'].tolist()) if hasattr(kmf, 'confidence_interval_') else None,
                ci_upper=sanitize_list(kmf.confidence_interval_['KM_estimate_upper_0.95'].tolist()) if hasattr(kmf, 'confidence_interval_') else None,
                n_samples=int(n_high),
                n_events=int(high_group['event'].sum())
            )

            kmf.fit(low_group['time'], event_observed=low_group['event'])
            median_low = kmf.median_survival_time_
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

        is_significant = (
            cox_p < self.p_value_threshold and
            (hazard_ratio >= self.hazard_ratio_upper or
             hazard_ratio <= self.hazard_ratio_lower)
        )
        expression_direction = "high_risk" if hazard_ratio > 1 else "low_risk"

        def safe_float(value):
            if value is None or pd.isna(value) or np.isinf(value):
                return None
            return float(value)

        adjusted_hr: Optional[float] = None
        adjusted_p: Optional[float] = None
        covariates_used: Optional[List[str]] = None
        if metadata_df is not None and covariate_columns:
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

        interaction_p: Optional[float] = None
        treatment_arms: Optional[List[Dict[str, Any]]] = None
        is_predictive = False
        if treatment_binary is not None and treatment_arm_names is not None:
            arm_aligned = treatment_binary.reindex(survival_data.index)
            if arm_aligned.notna().sum() >= self.min_samples_per_group * 2:
                fit = self._fit_interaction_cox(
                    expression_col=expression,
                    time_col=survival_data['time'],
                    event_col=survival_data['event'],
                    treatment_binary=arm_aligned,
                    arm_names=treatment_arm_names,
                )
                if fit is not None:
                    interaction_p, treatment_arms = fit
                    is_predictive = interaction_p < self.p_value_threshold

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
            interaction_p_value=safe_float(interaction_p),
            treatment_arms=treatment_arms,
            is_predictive=is_predictive,
        )

    def _analyze_all_genes_scalar(
        self,
        expression_matrix: pd.DataFrame,
        survival_df: pd.DataFrame,
        probe_to_gene: Optional[Dict[str, str]],
        metadata_aligned: Optional[pd.DataFrame],
        covariate_columns: Optional[List[str]],
        treatment_binary: Optional[pd.Series],
        treatment_arm_names: Optional[Dict[int, str]],
    ) -> Tuple[List[GeneSurvivalResult], int, Dict[str, float]]:
        """Exact per-gene `lifelines` loop — unchanged. Used for genes with
        missing expression values, genes whose vectorized Cox fit didn't
        converge, and as the whole-batch fallback if vectorization errors.

        Returns raw-significant genes (by the uncorrected p-value threshold)
        plus `raw_pvalues` covering every gene that got a valid Cox fit,
        significant or not — FDR correction (applied by the `_analyze_all_genes`
        caller) needs the full test set, not just the raw-significant subset.
        """
        significant_genes = []
        raw_pvalues: Dict[str, float] = {}
        n_analyzed = 0

        for gene_id in expression_matrix.index:
            try:
                gene_result = self._analyze_gene_survival(
                    gene_id=gene_id,
                    expression=expression_matrix.loc[gene_id],
                    survival_df=survival_df,
                    probe_to_gene=probe_to_gene,
                    metadata_df=metadata_aligned,
                    covariate_columns=covariate_columns,
                    treatment_binary=treatment_binary,
                    treatment_arm_names=treatment_arm_names,
                )

                n_analyzed += 1

                if gene_result:
                    raw_pvalues[gene_id] = gene_result.cox_p_value
                    if gene_result.is_significant:
                        significant_genes.append(gene_result)

            except Exception as e:
                logger.debug(f"Error analyzing gene {gene_id}: {e}")
                continue

        significant_genes.sort(key=lambda x: x.cox_p_value)
        return significant_genes, n_analyzed, raw_pvalues

    def _analyze_gene_survival(
        self,
        gene_id: str,
        expression: pd.Series,
        survival_df: pd.DataFrame,
        probe_to_gene: Optional[Dict[str, str]] = None,
        metadata_df: Optional[pd.DataFrame] = None,
        covariate_columns: Optional[List[str]] = None,
        treatment_binary: Optional[pd.Series] = None,
        treatment_arm_names: Optional[Dict[int, str]] = None,
    ) -> Optional[GeneSurvivalResult]:
        """
        Analyze survival association for a single gene

        Uses median expression to split samples into high/low groups,
        then performs log-rank test and Cox regression.

        When a treatment/arm column is supplied (`treatment_binary`), also fits an
        expression x treatment interaction Cox model to flag the gene as a
        predictive (treatment-effect-modifying) biomarker.
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
            (hazard_ratio >= self.hazard_ratio_upper or
             hazard_ratio <= self.hazard_ratio_lower)
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

        # Predictive (treatment-effect-modifying) biomarker test (F16b)
        interaction_p: Optional[float] = None
        treatment_arms: Optional[List[Dict[str, Any]]] = None
        is_predictive = False
        if treatment_binary is not None and treatment_arm_names is not None:
            arm_aligned = treatment_binary.reindex(survival_data.index)
            if arm_aligned.notna().sum() >= self.min_samples_per_group * 2:
                fit = self._fit_interaction_cox(
                    expression_col=expression,
                    time_col=survival_data['time'],
                    event_col=survival_data['event'],
                    treatment_binary=arm_aligned,
                    arm_names=treatment_arm_names,
                )
                if fit is not None:
                    interaction_p, treatment_arms = fit
                    is_predictive = interaction_p < self.p_value_threshold

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
            interaction_p_value=safe_float(interaction_p),
            treatment_arms=treatment_arms,
            is_predictive=is_predictive,
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
