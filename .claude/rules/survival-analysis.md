# Survival Analysis Rules

Domain rules for survival analysis using lifelines library.

## Key Concepts

- **Kaplan-Meier curves**: Survival probability over time (non-parametric)
- **Cox regression**: Hazard ratios showing gene-survival associations (semi-parametric)
- **HR > 1**: Gene expression increases risk (worse survival)
- **HR < 1**: Gene expression is protective (better survival)
- **Censoring**: Event not observed (patient lost to follow-up, marked as 0)

## Required Data Format

```python
survival_df = pd.DataFrame({
    'time': [10, 20, 15, 30, 25],        # Duration until event/censoring
    'event': [1, 0, 1, 1, 0],            # 1=event occurred, 0=censored
    'BRCA1': [2.5, 1.2, 3.1, 0.8, 1.5]  # Gene expression values
})
```

## Validation Requirements

Before running survival analysis, verify:
- [ ] Minimum 10 events (deaths/recurrences)
- [ ] No constant expression values (variance > 0)
- [ ] No extreme outliers in expression
- [ ] Time values are positive
- [ ] Event column is binary (0 or 1)

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ConvergenceError` | Too few events | Require minimum 10 events |
| `LinAlgError` | Collinear covariates | Remove correlated variables |
| All HR = 1.0 | No expression variance | Filter low-variance genes |
| Very large HR | Extreme expression | Log-transform or normalize |

## Statistical Considerations

- Always apply multiple testing correction (FDR) when analyzing many genes
- Check proportional hazards assumption for Cox models
- Report confidence intervals alongside p-values
- Use Efron's method when there are tied event times
