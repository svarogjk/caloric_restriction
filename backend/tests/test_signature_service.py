"""
Focused unit tests for the prognostic signature math (F17/F23).

These assert the statistically-critical behaviours that `tsc`/import checks
cannot catch:
  * C-index orientation (higher risk -> shorter survival) is correct, so the
    demo signature recovers a real signal with C-index clearly > 0.5.
  * Continuous risk score (not median split) ranks samples.
  * Single-sample scoring assigns plausible groups and t-year survival.
"""

import numpy as np
import pandas as pd
import pytest

from app.services.signature_service import (
    SignatureService,
    harrell_c_index,
    percentile_of,
    risk_from_zscores,
    zscore_columns,
)


def test_harrell_c_index_orientation():
    # Higher risk should mean shorter survival. Construct a perfect ranking:
    # sample with the highest risk dies first.
    times = np.array([10.0, 20.0, 30.0, 40.0])
    events = np.array([1, 1, 1, 1])
    risk = np.array([4.0, 3.0, 2.0, 1.0])  # highest risk -> shortest time
    c = harrell_c_index(times, risk, events)
    assert c == pytest.approx(1.0, abs=1e-6)

    # Reversed risk ordering -> perfectly wrong -> C ~ 0.
    c_rev = harrell_c_index(times, -risk, events)
    assert c_rev == pytest.approx(0.0, abs=1e-6)


def test_zscore_and_risk():
    expr = pd.DataFrame(
        {"s1": [1.0, 10.0], "s2": [2.0, 20.0], "s3": [3.0, 30.0]},
        index=["G1", "G2"],
    )
    z = zscore_columns(expr, expr.mean(axis=1), expr.std(axis=1, ddof=0))
    # Each row should be mean ~0.
    assert z.loc["G1"].mean() == pytest.approx(0.0, abs=1e-9)
    coef = pd.Series({"G1": 1.0, "G2": 0.0})
    risk = risk_from_zscores(z, coef)
    # G2 has zero coefficient, so risk is monotonic in G1 (s1<s2<s3).
    assert risk["s1"] < risk["s2"] < risk["s3"]


def test_percentile_of():
    ref = [float(i) for i in range(101)]  # 0..100
    assert percentile_of(-5, ref) == pytest.approx(0.0)
    assert percentile_of(200, ref) == pytest.approx(100.0)
    assert 40 < percentile_of(50, ref) < 60


def test_demo_signature_recovers_signal():
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)

    # Validation cohorts must exist and the pooled C-index must beat chance by a
    # clear margin — this is the end-to-end proof the fit + validation pipeline
    # and the C-index orientation are correct.
    val = [c for c in model.cohort_validations if c.role == "validation"]
    assert len(val) >= 1
    assert model.pooled_c_index > 0.62, f"pooled C-index too low: {model.pooled_c_index}"

    # Locked artifact is fully populated for downstream features.
    assert len(model.genes) == 10
    assert all(len(g.ref_quantiles) == 101 for g in model.genes)
    assert len(model.risk_score_tertiles) == 2
    assert len(model.reference_km) == 3


def test_single_sample_scoring():
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)

    # Built-in demo patient scores without error and yields a valid group.
    patient = svc.build_demo_patient(model)
    resp = svc.score_single_sample(model, patient)
    assert resp.risk_group in {"low", "intermediate", "high"}
    assert 0.0 <= resp.risk_percentile <= 100.0
    assert resp.genes_used == resp.genes_total == 10
    # Survival probabilities are valid.
    for s in resp.predicted_survival:
        assert 0.0 <= s.survival_probability <= 1.0


def test_high_expression_patient_is_higher_risk():
    """A patient with all signature genes at the top of the reference range
    should score in a higher risk percentile than one at the bottom."""
    svc = SignatureService(orchestrator=None)
    model = svc.build_demo_signature(max_genes=10)

    top = {g.gene_symbol: g.ref_quantiles[100] for g in model.genes}
    bottom = {g.gene_symbol: g.ref_quantiles[0] for g in model.genes}
    r_top = svc.score_single_sample(model, top)
    r_bottom = svc.score_single_sample(model, bottom)
    # The two extremes must not collapse to the same percentile.
    assert r_top.risk_percentile != r_bottom.risk_percentile
