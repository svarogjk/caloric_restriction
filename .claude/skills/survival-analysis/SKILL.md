---
name: survival-analysis
description: Survival analysis domain knowledge using the lifelines library. Use when implementing Kaplan-Meier curves, Cox regression, hazard ratios, log-rank tests, or gene expression survival studies.
---

# Survival Analysis

## Key Concepts

- **Kaplan-Meier estimator**: Non-parametric survival function estimation
- **Cox Proportional Hazards**: Semi-parametric model relating covariates to hazard
- **Hazard Ratio (HR)**: HR > 1 = increased risk, HR < 1 = protective
- **Log-rank test**: Compares survival distributions between groups
- **Censoring**: Outcome not observed (patient lost to follow-up)

## Required Data Format

```python
survival_df = pd.DataFrame({
    'time': [10, 20, 15, 30, 25],        # Duration until event/censoring
    'event': [1, 0, 1, 1, 0],            # 1=event, 0=censored
    'BRCA1': [2.5, 1.2, 3.1, 0.8, 1.5]  # Gene expression
})
```

## Kaplan-Meier Analysis

```python
from lifelines import KaplanMeierFitter

kmf = KaplanMeierFitter()
kmf.fit(time, event_observed=event, label="Survival")
survival_function = kmf.survival_function_
median_survival = kmf.median_survival_time_
```

## Cox Proportional Hazards

```python
from lifelines import CoxPHFitter

cph = CoxPHFitter()
cph.fit(data[['time', 'event', 'expression']], duration_col='time', event_col='event')

hazard_ratio = np.exp(cph.params_['expression'])
p_value = cph.summary.loc['expression', 'p']
ci_lower = np.exp(cph.confidence_intervals_.loc['expression', '95% lower-bound'])
ci_upper = np.exp(cph.confidence_intervals_.loc['expression', '95% upper-bound'])
```

## Gene Expression Dichotomization

```python
def dichotomize_expression(expression: pd.Series, method: str = "median") -> pd.Series:
    if method == "median":
        threshold = expression.median()
    elif method == "mean":
        threshold = expression.mean()
    return (expression > threshold).astype(int)
```

## Log-Rank Test

```python
from lifelines.statistics import logrank_test

results = logrank_test(time[high_mask], time[~high_mask], event[high_mask], event[~high_mask])
p_value = results.p_value
```

## Service Pattern

```python
class SurvivalAnalysisService:
    async def analyze_gene(self, gene_symbol: str, expression_data: pd.DataFrame,
                           time_col: str, event_col: str) -> GeneSurvivalResult:
        cph = CoxPHFitter()
        df = pd.DataFrame({
            'time': expression_data[time_col],
            'event': expression_data[event_col],
            'expression': expression_data[gene_symbol]
        })
        cph.fit(df, duration_col='time', event_col='event')
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

- Sufficient events (>=10 recommended)
- No tied event times (or use Efron's method)
- Proportional hazards assumption checked
- Multiple testing correction applied (if many genes)
