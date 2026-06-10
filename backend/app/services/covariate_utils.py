"""Shared clinical-covariate preparation for Cox models.

Reused by the per-dataset multivariate adjustment (F16,
`survival_analysis_service._fit_multivariate_cox`) and the combined
clinical + expression prognostic model (Oncologist Mode patient flow,
`signature_service`). Keeping usable-covariate selection and numeric coercion
in one place avoids drift between the two call sites.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

DEFAULT_MIN_COVERAGE = 0.7
# Below this fraction of values coercible to numbers, a covariate is treated as
# categorical (one-hot encoded) rather than numeric.
NUMERIC_COERCION_THRESHOLD = 0.8


def select_usable_covariates(
    metadata_df: pd.DataFrame,
    candidates: List[str],
    min_coverage: float = DEFAULT_MIN_COVERAGE,
) -> List[str]:
    """Covariates that exist in the metadata and are non-null in at least
    `min_coverage` of rows. Order follows `candidates`."""
    usable: List[str] = []
    for col in candidates:
        if col not in metadata_df.columns:
            continue
        if metadata_df[col].notna().mean() < min_coverage:
            continue
        usable.append(col)
    return usable


def coerce_numeric(series: pd.Series, threshold: float = NUMERIC_COERCION_THRESHOLD) -> Optional[pd.Series]:
    """Return a numeric version of `series` if at least `threshold` of its
    non-null values parse as numbers (GEO metadata is often string-typed), else
    None to signal the column should be treated as categorical."""
    non_null = series.dropna()
    if non_null.empty:
        return None
    coerced = pd.to_numeric(non_null, errors="coerce")
    if coerced.notna().mean() < threshold:
        return None
    # Re-coerce over the full index so alignment is preserved.
    return pd.to_numeric(series, errors="coerce")
