"""Cross-cohort heterogeneity (Cochran Q / I² / tau²).

`_compute_heterogeneity` existed but had zero call sites, so
`GeneSurvivalResponse.heterogeneity_stats` was always None even though the
forest plot and the export CSV already read it. These lock in the behaviour now
that it is wired into `_find_common_survival_genes`.
"""
import math

import pytest

from app.services.geo_survival_workflow_orchestrator import GEOSurvivalWorkflowOrchestrator

het = GEOSurvivalWorkflowOrchestrator._compute_heterogeneity


def _ci(hr: float, width: float = 0.2) -> tuple[float, float]:
    """A symmetric-on-the-log-scale CI of the given half-width around `hr`."""
    return math.exp(math.log(hr) - width), math.exp(math.log(hr) + width)


def test_identical_effects_give_zero_heterogeneity():
    hrs = [1.5, 1.5, 1.5, 1.5]
    cis = [_ci(hr) for hr in hrs]
    out = het([math.log(h) for h in hrs], [c[0] for c in cis], [c[1] for c in cis])

    assert out["q_statistic"] == pytest.approx(0.0, abs=1e-6)
    assert out["i_squared"] == 0.0
    assert out["tau_squared"] == 0.0
    assert out["p_heterogeneity"] > 0.9


def test_divergent_effects_with_tight_cis_are_flagged():
    # Opposite directions, narrow intervals ⇒ the cohorts genuinely disagree.
    hrs = [0.4, 0.45, 2.5, 2.8]
    cis = [_ci(hr, width=0.08) for hr in hrs]
    out = het([math.log(h) for h in hrs], [c[0] for c in cis], [c[1] for c in cis])

    assert out["i_squared"] > 50
    assert out["p_heterogeneity"] < 0.05
    assert out["tau_squared"] > 0


def test_fewer_than_two_datasets_returns_all_none():
    for out in (het([], [], []), het([math.log(1.5)], [1.2], [1.9])):
        assert out == {
            "q_statistic": None,
            "i_squared": None,
            "p_heterogeneity": None,
            "tau_squared": None,
        }


def test_unusable_ci_bounds_are_dropped_without_desynchronising():
    # The middle cohort has an unusable CI. It must be dropped as a WHOLE triple:
    # if the three lists were filtered independently, cohort 3's log-HR would be
    # paired with cohort 2's interval and the result would be silently wrong.
    good = [1.5, 1.5]
    lo, hi = zip(*[_ci(h) for h in good])

    with_bad = het(
        [math.log(good[0]), math.log(5.0), math.log(good[1])],
        [lo[0], 0.0, lo[1]],
        [hi[0], None, hi[1]],
    )
    without_bad = het([math.log(h) for h in good], list(lo), list(hi))
    assert with_bad == without_bad
    assert with_bad["i_squared"] == 0.0


def test_two_usable_of_three_still_computes():
    out = het([math.log(1.2), math.log(3.0)], [1.15, 2.8], [1.25, 3.2])
    assert out["i_squared"] is not None
    assert out["q_statistic"] > 0
