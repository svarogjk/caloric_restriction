"""
Regression tests for the vectorized log-rank + Cox path in
SurvivalAnalysisService._analyze_all_genes_vectorized.

These assert numerical parity against the exact per-gene `lifelines` path
(_analyze_all_genes_scalar) that vectorization must reproduce: same
significant-gene set, same n_analyzed count, and hazard ratios / CIs /
p-values matching within a tight tolerance. Covers the cases that stress the
Efron tie-handling and the NaN/non-convergence fallback routing.
"""

import numpy as np
import pandas as pd
import pytest

from app.services.survival_analysis_service import SurvivalAnalysisService


def _synthetic_dataset(
    n_samples=120,
    n_genes=150,
    seed=0,
    tie_rounding=None,
    n_nan_genes=0,
    n_signal=1,
    isolated_signal=True,
    effect_scale=1.0,
):
    rng = np.random.default_rng(seed)
    idx = [f"s{i}" for i in range(n_samples)]

    beta_true = np.zeros(n_genes)
    beta_true[:n_signal] = rng.choice([-1.2, -0.8, 0.8, 1.2, 1.6], size=n_signal) * effect_scale

    X = rng.normal(0, 1, size=(n_genes, n_samples))
    baseline = rng.exponential(scale=50, size=n_samples)

    if isolated_signal:
        lin_pred = beta_true[0] * X[0] if n_signal > 0 else np.zeros(n_samples)
    else:
        lin_pred = (beta_true[:n_signal, None] * X[:n_signal]).sum(axis=0)

    time = baseline * np.exp(-lin_pred)
    censor_time = rng.exponential(scale=80, size=n_samples)
    event = (time <= censor_time).astype(float)
    obs_time = np.minimum(time, censor_time)

    if tie_rounding is not None:
        obs_time = np.maximum(np.round(obs_time / tie_rounding) * tie_rounding, 0.1)

    survival_df = pd.DataFrame({"time": obs_time, "event": event}, index=idx)
    expr_df = pd.DataFrame(X, index=[f"g{i}" for i in range(n_genes)], columns=idx)

    if n_nan_genes > 0:
        nan_positions = rng.choice(n_genes, size=n_nan_genes, replace=False)
        for pos in nan_positions:
            nan_samples = rng.choice(n_samples, size=5, replace=False)
            expr_df.iloc[pos, nan_samples] = np.nan

    return expr_df, survival_df


@pytest.fixture
def svc():
    return SurvivalAnalysisService()


def _assert_matches_scalar(svc, expr_df, survival_df, hr_rtol=1e-3, p_atol=1e-3):
    scalar_genes, scalar_n = svc._analyze_all_genes_scalar(
        expr_df, survival_df, None, None, None, None, None
    )
    vec_genes, vec_n = svc._analyze_all_genes_vectorized(
        expr_df, survival_df, None, None, None, None, None
    )

    assert vec_n == scalar_n

    scalar_by_id = {g.gene_id: g for g in scalar_genes}
    vec_by_id = {g.gene_id: g for g in vec_genes}
    assert set(scalar_by_id) == set(vec_by_id), (
        f"significant-gene sets differ: only_scalar={set(scalar_by_id) - set(vec_by_id)} "
        f"only_vec={set(vec_by_id) - set(scalar_by_id)}"
    )

    for gene_id, expected in scalar_by_id.items():
        actual = vec_by_id[gene_id]
        assert actual.hazard_ratio == pytest.approx(expected.hazard_ratio, rel=hr_rtol)
        assert actual.hazard_ratio_ci_lower == pytest.approx(expected.hazard_ratio_ci_lower, rel=hr_rtol)
        assert actual.hazard_ratio_ci_upper == pytest.approx(expected.hazard_ratio_ci_upper, rel=hr_rtol)
        assert actual.cox_p_value == pytest.approx(expected.cox_p_value, abs=p_atol)
        assert actual.log_rank_p_value == pytest.approx(expected.log_rank_p_value, abs=p_atol)

    return vec_genes, vec_n


def test_vectorized_matches_scalar_no_ties(svc):
    expr_df, survival_df = _synthetic_dataset(seed=1, n_genes=150)
    _assert_matches_scalar(svc, expr_df, survival_df)


def test_vectorized_matches_scalar_with_ties(svc):
    # Rounding times induces heavy ties, exercising Efron's tie correction
    # on a gene whose isolated effect is strong enough to reach significance.
    expr_df, survival_df = _synthetic_dataset(seed=2, n_genes=150, tie_rounding=3)
    vec_genes, _ = _assert_matches_scalar(svc, expr_df, survival_df)
    assert len(vec_genes) >= 1, "expected the isolated strong-effect gene to be flagged significant"


def test_vectorized_matches_scalar_with_nan_genes(svc):
    # Genes with missing expression values must route through the exact
    # scalar fallback rather than the batched fast path.
    expr_df, survival_df = _synthetic_dataset(seed=3, n_genes=100, n_nan_genes=6, n_signal=0)
    _assert_matches_scalar(svc, expr_df, survival_df)


def test_vectorized_matches_scalar_small_sample(svc):
    # Edge of the min_samples_per_group threshold.
    expr_df, survival_df = _synthetic_dataset(seed=4, n_samples=24, n_genes=120, n_signal=30, isolated_signal=False)
    _assert_matches_scalar(svc, expr_df, survival_df)
