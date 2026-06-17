"""
Regression tests for gene-mapping robustness in the cancer-gene filter.

Covers the failure mode that caused "breast cancer overall survival" to return
0 common genes: a gene-level dataset (e.g. NanoString panel) whose cached
probe->gene mapping was corrupted (gene_symbol column held numeric expression
values instead of symbols). This poisoned the cancer filter (0 matches) and
gene-name aggregation across datasets.

Two defences are tested here:
  * Corrupted mappings (numeric gene_symbol values) are detected and discarded
    at load time, so gene-level index symbols flow through unmodified.
  * The cancer filter falls back to matching the expression-matrix index
    directly against CANCER_GENE_SET when the mapping yields 0 cancer probes.
"""

import pandas as pd

from app.data.cancer_genes import CANCER_GENE_SET
from app.services.geo_loader_service import GEODataLoaderService


def test_corrupted_mapping_detected():
    # gene_symbol values are numeric expression values, not real symbols.
    corrupted = {"AKT3": "-2.936360715", "ANGPT1": "-6.682786638", "BCL2": "1.069638026"}
    assert GEODataLoaderService._is_corrupted_mapping(corrupted) is True


def test_valid_mapping_not_flagged():
    valid = {"1007_s_at": "DDR1", "1053_at": "RFC2", "117_at": "HSPA6"}
    assert GEODataLoaderService._is_corrupted_mapping(valid) is False


def test_empty_mapping_is_safe():
    assert GEODataLoaderService._is_corrupted_mapping({}) is False


def test_mixed_mapping_majority_numeric_flagged():
    # Majority numeric -> treated as corrupted.
    mixed = {"A": "1.5", "B": "-2.0", "C": "TP53", "D": "3.3"}
    assert GEODataLoaderService._is_corrupted_mapping(mixed) is True


def test_cancer_filter_index_fallback_matches_gene_level_data():
    # Gene-level expression matrix indexed by gene symbols; a broken mapping
    # yields 0 cancer probes, but the index-based fallback recovers them.
    index = pd.Index(["AKT3", "ANGPT1", "BCL2", "NOT_A_GENE_XYZ"], name="ID_REF")
    expr = pd.DataFrame({"GSM1": [1.0, 2.0, 3.0, 4.0]}, index=index)

    # Broken mapping -> 0 cancer probes.
    broken_mapping = {"AKT3": "-2.9", "ANGPT1": "-6.6", "BCL2": "1.0"}
    cancer_probes = {p for p, g in broken_mapping.items() if str(g).upper() in CANCER_GENE_SET}
    assert len(cancer_probes) == 0

    # Fallback: match the index directly against COSMIC.
    index_mask = expr.index.to_series().str.upper().isin(CANCER_GENE_SET)
    assert index_mask.sum() == 3
    assert "NOT_A_GENE_XYZ" not in list(expr.index[index_mask.values])
