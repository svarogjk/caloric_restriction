# Survival Analysis Skill

Use this skill when working with survival analysis, Kaplan-Meier curves, Cox regression, hazard ratios, or gene expression survival studies. Helps implement and debug survival analysis code using the lifelines library.

## Domain Knowledge

### Key Concepts
- **Kaplan-Meier estimator**: Non-parametric method for estimating survival function
- **Cox Proportional Hazards**: Semi-parametric model relating covariates to hazard
- **Hazard Ratio (HR)**: Ratio of hazard rates between groups
  - HR > 1: Increased risk (worse survival)
  - HR < 1: Decreased risk (better survival / protective)
- **Log-rank test**: Compares survival distributions between groups
- **Censoring**: When outcome is not observed (patient lost to follow-up)

### Required Data Format
```python
# Survival data must have:
# - time_column: Duration until event or censoring
# - event_column: Binary (1 = event occurred, 0 = censored)
# - expression values: Continuous gene expression

survival_df = pd.DataFrame({
    'time': [10, 20, 15, 30, 25],        # Days/months to event
    'event': [1, 0, 1, 1, 0],            # 1=death, 0=alive/censored
    'BRCA1': [2.5, 1.2, 3.1, 0.8, 1.5]  # Gene expression
})
```

## Code Patterns

### Kaplan-Meier Analysis
```python
from lifelines import KaplanMeierFitter

def fit_kaplan_meier(
    time: pd.Series,
    event: pd.Series,
    label: str = "Survival"
) -> KaplanMeierFitter:
    """Fit Kaplan-Meier survival curve."""
    kmf = KaplanMeierFitter()
    kmf.fit(time, event_observed=event, label=label)
    return kmf

# Get survival function values
survival_function = kmf.survival_function_
median_survival = kmf.median_survival_time_
confidence_intervals = kmf.confidence_interval_survival_function_
```

### Cox Proportional Hazards
```python
from lifelines import CoxPHFitter

def fit_cox_model(
    data: pd.DataFrame,
    duration_col: str,
    event_col: str,
    covariates: list[str]
) -> CoxPHFitter:
    """Fit Cox proportional hazards model."""
    cph = CoxPHFitter()
    cols = [duration_col, event_col] + covariates
    cph.fit(data[cols], duration_col=duration_col, event_col=event_col)
    return cph

# Extract results
hazard_ratio = np.exp(cph.params_['gene_expression'])
p_value = cph.summary.loc['gene_expression', 'p']
ci_lower = np.exp(cph.confidence_intervals_.loc['gene_expression', '95% lower-bound'])
ci_upper = np.exp(cph.confidence_intervals_.loc['gene_expression', '95% upper-bound'])
```

### Gene Expression Dichotomization
```python
def dichotomize_expression(
    expression: pd.Series,
    method: str = "median"
) -> pd.Series:
    """Split expression into high/low groups."""
    if method == "median":
        threshold = expression.median()
    elif method == "mean":
        threshold = expression.mean()
    elif method == "tertile":
        threshold = expression.quantile([0.33, 0.67])

    return (expression > threshold).astype(int)
```

### Log-Rank Test
```python
from lifelines.statistics import logrank_test

def compare_survival_groups(
    time: pd.Series,
    event: pd.Series,
    group: pd.Series
) -> dict:
    """Compare survival between two groups."""
    high_mask = group == 1

    results = logrank_test(
        time[high_mask], time[~high_mask],
        event[high_mask], event[~high_mask]
    )

    return {
        'test_statistic': results.test_statistic,
        'p_value': results.p_value
    }
```

## Project Integration

### Service Pattern
```python
# In backend/app/services/survival_analysis_service.py

class SurvivalAnalysisService:
    async def analyze_gene(
        self,
        gene_symbol: str,
        expression_data: pd.DataFrame,
        time_col: str,
        event_col: str,
    ) -> GeneSurvivalResult:
        """Analyze survival association for a gene."""
        # Prepare data
        gene_expr = expression_data[gene_symbol]

        # Fit Cox model
        cph = CoxPHFitter()
        df = pd.DataFrame({
            'time': expression_data[time_col],
            'event': expression_data[event_col],
            'expression': gene_expr
        })
        cph.fit(df, duration_col='time', event_col='event')

        # Extract results
        return GeneSurvivalResult(
            gene_symbol=gene_symbol,
            hazard_ratio=float(np.exp(cph.params_['expression'])),
            p_value=float(cph.summary.loc['expression', 'p']),
            ci_lower=float(np.exp(cph.confidence_intervals_.loc['expression', '95% lower-bound'])),
            ci_upper=float(np.exp(cph.confidence_intervals_.loc['expression', '95% upper-bound']))
        )
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ConvergenceError` | Too few events | Require minimum 10 events |
| `LinAlgError` | Collinear covariates | Remove correlated variables |
| All HR = 1.0 | No expression variance | Filter low-variance genes |
| Very large HR | Extreme expression values | Log-transform or normalize |

## Validation Checklist
- [ ] Sufficient events (>=10 recommended)
- [ ] No tied event times (or use Efron's method)
- [ ] Proportional hazards assumption checked
- [ ] Multiple testing correction applied (if many genes)
