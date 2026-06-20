"""
Focused unit tests for the predictive (treatment-effect-modifying) biomarker
statistic (F16b) added to SurvivalAnalysisService.

These assert the statistically-critical behaviours that import checks cannot
catch:
  * A gene whose expression effect on survival exists ONLY in the treated arm
    yields a SIGNIFICANT expression x treatment interaction (predictive).
  * A gene with the SAME effect in both arms yields a NON-significant interaction
    (prognostic, not predictive).
  * Treatment-column detection + binarization recover two arms from free-text
    GEO metadata, and lopsided / single-value columns are rejected.
"""

import numpy as np
import pandas as pd
import pytest

from app.services.survival_analysis_service import SurvivalAnalysisService


def _synthetic_cohort(n: int = 200, seed: int = 0):
    """Half treated (arm=1), half untreated (arm=0), all events observed."""
    rng = np.random.default_rng(seed)
    treat = np.repeat([0, 1], n // 2).astype(float)
    expr = rng.normal(0, 1, n)
    base = rng.exponential(50, n)
    idx = [f"s{i}" for i in range(n)]
    return idx, treat, expr, base


@pytest.fixture
def svc():
    return SurvivalAnalysisService()


def test_interaction_flags_predictive_gene(svc):
    idx, treat, expr, base = _synthetic_cohort()
    # Effect ONLY in the treated arm: higher expression shortens time when arm==1.
    eff = np.where(treat == 1, np.exp(-0.9 * expr), 1.0)
    time = base * eff
    res = svc._fit_interaction_cox(
        pd.Series(expr, index=idx),
        pd.Series(time, index=idx),
        pd.Series(np.ones(len(idx)), index=idx),
        pd.Series(treat, index=idx),
        {0: "Untreated", 1: "Treated"},
    )
    assert res is not None
    interaction_p, arms = res
    assert interaction_p < 0.05, f"expected significant interaction, got p={interaction_p}"
    assert len(arms) == 2
    treated = next(a for a in arms if a["name"] == "Treated")
    untreated = next(a for a in arms if a["name"] == "Untreated")
    # Treated arm carries the risk; untreated arm is ~null.
    assert treated["hazard_ratio"] > untreated["hazard_ratio"]


def test_interaction_ignores_prognostic_gene(svc):
    idx, treat, expr, base = _synthetic_cohort(seed=1)
    # SAME effect in both arms -> prognostic, not predictive.
    eff = np.exp(-0.9 * expr)
    time = base * eff
    res = svc._fit_interaction_cox(
        pd.Series(expr, index=idx),
        pd.Series(time, index=idx),
        pd.Series(np.ones(len(idx)), index=idx),
        pd.Series(treat, index=idx),
        {0: "Untreated", 1: "Treated"},
    )
    assert res is not None
    interaction_p, _arms = res
    assert interaction_p > 0.05, f"expected non-significant interaction, got p={interaction_p}"


def test_detect_and_binarize_treatment_column(svc):
    idx, treat, _expr, _base = _synthetic_cohort()
    meta = pd.DataFrame(
        {
            "treatment_ch1": [
                "treatment: tamoxifen" if t else "treatment: none" for t in treat
            ],
            "age_ch1": ["age: 60"] * len(idx),
        },
        index=idx,
    )
    col = svc._detect_treatment_column(meta)
    assert col == "treatment_ch1"

    binarized = svc._binarize_treatment(meta[col])
    assert binarized is not None
    binary, arm_names = binarized
    assert set(arm_names.keys()) == {0, 1}
    assert int((binary == 1).sum()) == len(idx) // 2
    assert int((binary == 0).sum()) == len(idx) // 2


def test_binarize_rejects_single_value_column(svc):
    idx = [f"s{i}" for i in range(40)]
    series = pd.Series(["treatment: chemo"] * len(idx), index=idx)
    assert svc._binarize_treatment(series) is None


def test_analyze_gene_survival_sets_is_predictive(svc):
    idx, treat, expr, base = _synthetic_cohort()
    eff = np.where(treat == 1, np.exp(-0.9 * expr), 1.0)
    time = base * eff
    survival_df = pd.DataFrame(
        {"time": time, "event": np.ones(len(idx))}, index=idx
    )
    result = svc._analyze_gene_survival(
        gene_id="GENEX",
        expression=pd.Series(expr, index=idx),
        survival_df=survival_df,
        treatment_binary=pd.Series(treat, index=idx),
        treatment_arm_names={0: "Untreated", 1: "Treated"},
    )
    assert result is not None
    assert result.is_predictive is True
    assert result.interaction_p_value is not None and result.interaction_p_value < 0.05
    assert result.treatment_arms and len(result.treatment_arms) == 2
