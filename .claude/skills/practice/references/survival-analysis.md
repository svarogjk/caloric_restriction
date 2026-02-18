# Survival Analysis Exercises

Exercises using lifelines, based on patterns from `backend/app/services/survival_analysis_service.py`.

## Beginner

### Exercise 1: Fit Kaplan-Meier and Extract Results
**Task**: Given a DataFrame with `time` and `event` columns, fit `KaplanMeierFitter`, return survival function DataFrame, median survival time (None if not reached), sample count, and event count.
**Starter code**:
```python
from lifelines import KaplanMeierFitter
import pandas as pd

def fit_kaplan_meier(survival_df: pd.DataFrame) -> dict:
    # TODO: Create KaplanMeierFitter and fit with time/event columns
    # TODO: Extract survival_function_, median_survival_time_ (handle inf → None)
    # TODO: Return dict with survival_function, median_survival, n_samples, n_events
    return {}
```
**Test criteria**:
- Survival function starts at 1.0, monotonically non-increasing
- Median is float or None, counts match input data
**Key concepts**: KaplanMeierFitter, survival function, median survival, censoring

### Exercise 2: Compare Two Groups
**Task**: Fit separate KM models for two patient groups, compute median survival for each, return comparison with difference.
**Starter code**:
```python
def compare_groups(group_a: pd.DataFrame, group_b: pd.DataFrame) -> dict:
    # TODO: Fit KMF for each group
    # TODO: Extract medians (handle inf → None)
    # TODO: Calculate difference if both medians exist
    return {'median_a': None, 'median_b': None, 'difference': None}
```
**Test criteria**:
- Medians correctly extracted, difference is None when either median not reached
**Key concepts**: KaplanMeierFitter, group comparison, handling infinity

## Intermediate

### Exercise 3: Cox Regression with Hazard Ratios
**Task**: Fit `CoxPHFitter` to data with time, event, and covariates. Extract hazard ratio (exp of coefficient), 95% CI bounds, and p-value for each covariate.
**Starter code**:
```python
from lifelines import CoxPHFitter
from dataclasses import dataclass

@dataclass
class CoxResult:
    covariate: str
    hazard_ratio: float
    ci_lower: float
    ci_upper: float
    p_value: float

def fit_cox(df: pd.DataFrame, duration_col: str = "time", event_col: str = "event") -> list[CoxResult]:
    # TODO: Fit CoxPHFitter
    # TODO: For each covariate in summary: extract HR = exp(coef), CI = exp(bounds), p
    return []
```
**Test criteria**:
- HR = exp(coefficient), CI bounds correctly exp-transformed
- One CoxResult per covariate (excluding duration/event columns)
**Key concepts**: CoxPHFitter, hazard ratio, exp-transformation, confidence intervals

### Exercise 4: Log-Rank Test
**Task**: Perform log-rank test between high and low expression groups. Return test statistic, p-value, significance flag, and group sizes.
**Starter code**:
```python
from lifelines.statistics import logrank_test

def perform_logrank(high: pd.DataFrame, low: pd.DataFrame, alpha: float = 0.05) -> dict:
    # TODO: Call logrank_test with durations and events from both groups
    # TODO: Return test_statistic, p_value, is_significant, n_high, n_low
    return {}
```
**Test criteria**:
- Returns correct results for clearly separated and overlapping groups
- is_significant correctly reflects p < alpha
**Key concepts**: logrank_test, hypothesis testing, significance

## Advanced

### Exercise 5: Gene Expression Survival Pipeline
**Task**: Build a complete single-gene analysis: align expression with survival data, median-split into high/low, fit KM for both groups, run log-rank test, fit Cox regression, return structured `GeneSurvivalResult` with KM curve data.
**Starter code**:
```python
@dataclass
class KMCurveData:
    times: list[float]
    survival_probabilities: list[float]
    n_samples: int
    n_events: int

@dataclass
class GeneSurvivalResult:
    gene_id: str
    hazard_ratio: float
    ci_lower: float
    ci_upper: float
    log_rank_p: float
    cox_p: float
    is_significant: bool
    direction: str  # "high_risk" or "low_risk"
    km_high: KMCurveData
    km_low: KMCurveData

def analyze_gene(gene_id: str, expression: pd.Series, survival_df: pd.DataFrame,
                 p_threshold: float = 0.05, hr_threshold: float = 1.5,
                 min_per_group: int = 5) -> Optional[GeneSurvivalResult]:
    # TODO: Align expression and survival by common index
    # TODO: Remove NaN expression values
    # TODO: Median split → high/low masks
    # TODO: Validate min samples per group
    # TODO: Log-rank test, Cox regression, KM fitting for both groups
    # TODO: Significance = cox_p < threshold AND HR exceeds threshold
    # TODO: Direction = "high_risk" if HR > 1 else "low_risk"
    return None
```
**Test criteria**:
- Returns None for insufficient samples, correct HR direction
- KM curve data lengths match, significance requires both criteria
**Key concepts**: Median split, KM fitting, log-rank, Cox regression, pipeline

### Exercise 6: Multi-Gene Analysis with FDR Correction
**Task**: Analyze all genes in an expression matrix, collect p-values, apply Benjamini-Hochberg FDR correction, and return sorted significant results.
**Starter code**:
```python
from scipy.stats import false_discovery_control

def analyze_multi_gene(expression_matrix: pd.DataFrame, survival_df: pd.DataFrame,
                       probe_to_gene: dict[str, str] | None = None,
                       p_threshold: float = 0.05) -> list[dict]:
    # TODO: Align samples (columns) with survival index
    # TODO: Loop genes (rows): median split → Cox → collect raw p-values
    # TODO: Apply BH FDR correction to all raw p-values
    # TODO: Update results with adjusted p-values
    # TODO: Filter significant, sort by adjusted p ascending
    return []
```
**Test criteria**:
- FDR-adjusted p-values >= raw p-values, sorted ascending
- Probe-to-gene mapping applied correctly
- Handles NaN values and insufficient samples gracefully
**Key concepts**: Multiple testing correction, BH FDR, genome-wide analysis
