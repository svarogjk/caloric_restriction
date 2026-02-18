---
paths:
  - "backend/app/**/*survival*"
  - "frontend/src/**/Kaplan*"
  - "frontend/src/**/Volcano*"
---

# Survival Analysis Rules

Domain rules for survival analysis using lifelines library.

## Key Concepts

- **Kaplan-Meier**: Survival probability over time (non-parametric)
- **Cox regression**: Hazard ratios (HR) for gene-survival associations
- **HR > 1**: Increased risk | **HR < 1**: Protective
- **Censoring**: Event not observed (lost to follow-up), marked as 0

## Required Data Format

DataFrame with columns: `time` (positive, duration), `event` (binary 0/1), gene expression columns (float).

## Validation Before Analysis

- Minimum 10 events (deaths/recurrences)
- Expression variance > 0 (no constant values)
- Time values positive, event column binary
- No extreme outliers in expression

## Common Errors

| Error | Fix |
|-------|-----|
| `ConvergenceError` | Require minimum 10 events |
| `LinAlgError` | Remove correlated covariates |
| All HR = 1.0 | Filter low-variance genes |
| Very large HR | Log-transform or normalize expression |

## Statistical Requirements

- Apply FDR correction when analyzing many genes
- Check proportional hazards assumption for Cox models
- Report confidence intervals alongside p-values
- Use Efron's method for tied event times
