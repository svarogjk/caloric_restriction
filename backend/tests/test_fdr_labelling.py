"""The single-gene FDR trap.

`gene_filter` restricts the expression matrix BEFORE Cox testing, so a
one-gene run passes exactly one p-value to Benjamini-Hochberg. BH over a single
hypothesis is a no-op — the "FDR-adjusted" value comes back numerically equal to
the nominal Cox p. Reporting that number as an FDR q-value would be a false
claim about multiplicity correction.

These tests pin the arithmetic, and pin the diagnostics fields a client must use
to choose the label instead of guessing from the gene count.
"""
import pytest
from statsmodels.stats.multitest import multipletests

from app.api.routes import _build_analysis_response
from app.services.geo_survival_workflow_orchestrator import (
    CrossDatasetSurvivalAnalysis,
    GeneSurvivalOccurrence,
)
from app.services.survival_analysis_service import SurvivalAnalysisResult
from datetime import datetime, timezone


def test_bh_over_one_hypothesis_returns_the_input_unchanged():
    for p in (0.001, 0.032, 0.5, 0.99):
        _, adj, _, _ = multipletests([p], method="fdr_bh", alpha=0.05)
        assert adj[0] == pytest.approx(p)


def test_bh_over_many_hypotheses_does_adjust():
    pvals = [0.001, 0.01, 0.03, 0.2, 0.9]
    _, adj, _, _ = multipletests(pvals, method="fdr_bh", alpha=0.05)
    assert all(a >= p for a, p in zip(adj, pvals))
    assert adj[2] > pvals[2]


def _analysis(n_genes_analyzed: int) -> CrossDatasetSurvivalAnalysis:
    survival_result = SurvivalAnalysisResult(
        accession="GSE1", title="t", platform="GPL1", n_samples=100,
        n_genes_analyzed=n_genes_analyzed, n_significant_genes=1,
        significant_genes=[], survival_time_unit="months",
        event_type="death", analysis_method="cox",
    )
    return CrossDatasetSurvivalAnalysis(
        query="q", n_datasets_analyzed=1, n_datasets_with_survival=1,
        common_survival_genes=[
            GeneSurvivalOccurrence(
                gene_id="MKI67", gene_symbol="MKI67", n_datasets=1,
                avg_hazard_ratio=1.8, avg_cox_p_value=0.01, avg_log_rank_p_value=0.02,
                datasets=["GSE1"], risk_direction_consistency=1.0,
                predominant_risk="high_risk", per_dataset_results=[],
                min_fdr_adjusted_p_value=0.01,
            )
        ],
        all_survival_results=[survival_result],
        processing_time=1.0, timestamp=datetime.now(timezone.utc),
    )


def test_diagnostics_report_a_restricted_run():
    resp = _build_analysis_response(_analysis(1), gene_filter_applied=True)
    assert resp.diagnostics is not None
    assert resp.diagnostics.gene_filter_applied is True
    assert resp.diagnostics.n_genes_tested == 1


def test_diagnostics_report_a_genome_wide_run():
    resp = _build_analysis_response(_analysis(19_000), gene_filter_applied=False)
    assert resp.diagnostics.gene_filter_applied is False
    assert resp.diagnostics.n_genes_tested == 19_000


def test_diagnostics_are_present_even_when_genes_were_found():
    # They used to be built only for empty results, which left a successful run
    # with no way to say whether its p-values were corrected.
    resp = _build_analysis_response(_analysis(19_000))
    assert resp.common_genes
    assert resp.diagnostics is not None
    assert resp.diagnostics.reason is None
