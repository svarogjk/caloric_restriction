"""
Export service for publication-ready ZIP packages.
Generates: genes.csv, per_dataset_results.csv, methods.txt, analysis_params.json, README.txt
"""
import csv
import io
import json
import zipfile
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExportService:

    def build_export_zip(self, result_data: dict) -> bytes:
        """
        Build an in-memory ZIP containing publication-ready files from a stored analysis result.
        Returns the ZIP as bytes.
        """
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.txt", self._build_readme(result_data))
            zf.writestr("genes.csv", self._build_genes_csv(result_data))
            zf.writestr("per_dataset_results.csv", self._build_per_dataset_csv(result_data))
            zf.writestr("methods.txt", self._build_methods_text(result_data))
            zf.writestr("analysis_params.json", self._build_params_json(result_data))

        return buffer.getvalue()

    def _build_readme(self, r: dict) -> str:
        return f"""GEO Survival Analysis — Export Package
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Query: {r.get('query', '')}

FILES IN THIS PACKAGE:
  genes.csv               Cross-dataset gene summary with hazard ratios and p-values
  per_dataset_results.csv Per-dataset survival analysis results for all genes
  methods.txt             Pre-written Methods section for publication (edit as needed)
  analysis_params.json    All analysis parameters for reproducibility
  README.txt              This file

CITATION:
  Please cite this tool and the NCBI GEO database in your Methods section.
  Suggested citation text is provided in methods.txt.

GEO Survival Analysis: https://github.com/[your-repo]
NCBI GEO: https://www.ncbi.nlm.nih.gov/geo/
"""

    def _build_genes_csv(self, r: dict) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Gene Symbol", "Gene ID", "N Datasets", "Avg Hazard Ratio",
            "Avg Cox P-value", "Avg Log-Rank P-value", "Risk Direction Consistency %",
            "Predominant Risk", "Dataset IDs",
            "I² (%)", "Q Statistic", "p Heterogeneity",
        ])
        for gene in r.get("common_genes", []):
            het = gene.get("heterogeneity_stats") or {}
            writer.writerow([
                gene.get("gene_symbol", ""),
                gene.get("gene_id", ""),
                gene.get("n_datasets", ""),
                f"{gene.get('avg_hazard_ratio', ''):.4f}" if gene.get("avg_hazard_ratio") else "",
                f"{gene.get('avg_cox_p_value', ''):.4e}" if gene.get("avg_cox_p_value") else "",
                f"{gene.get('avg_log_rank_p_value', ''):.4e}" if gene.get("avg_log_rank_p_value") else "",
                f"{gene.get('risk_direction_consistency', 0) * 100:.1f}",
                gene.get("predominant_risk", ""),
                ", ".join(gene.get("datasets", [])),
                f"{het.get('i_squared', ''):.1f}" if het.get("i_squared") is not None else "",
                f"{het.get('q_statistic', ''):.3f}" if het.get("q_statistic") is not None else "",
                f"{het.get('p_heterogeneity', ''):.4f}" if het.get("p_heterogeneity") is not None else "",
            ])
        return output.getvalue()

    def _build_per_dataset_csv(self, r: dict) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Gene Symbol", "Gene ID", "Dataset ID", "Dataset Title",
            "Hazard Ratio", "HR CI Lower", "HR CI Upper", "Cox P-value",
            "Log-Rank P-value", "Risk Direction", "N Samples",
            "Adjusted HR", "Multivariate Cox P-value", "Covariates Used",
        ])
        for gene in r.get("common_genes", []):
            for ds in gene.get("per_dataset_results") or []:
                writer.writerow([
                    gene.get("gene_symbol", ""),
                    gene.get("gene_id", ""),
                    ds.get("dataset_id", ""),
                    ds.get("dataset_title", ""),
                    f"{ds.get('hazard_ratio', ''):.4f}" if ds.get("hazard_ratio") else "",
                    f"{ds.get('hazard_ratio_ci_lower', ''):.4f}" if ds.get("hazard_ratio_ci_lower") else "",
                    f"{ds.get('hazard_ratio_ci_upper', ''):.4f}" if ds.get("hazard_ratio_ci_upper") else "",
                    f"{ds.get('cox_p_value', ''):.4e}" if ds.get("cox_p_value") else "",
                    f"{ds.get('log_rank_p_value', ''):.4e}" if ds.get("log_rank_p_value") else "",
                    ds.get("risk_direction", ""),
                    ds.get("n_samples", ""),
                    f"{ds.get('adjusted_hazard_ratio', ''):.4f}" if ds.get("adjusted_hazard_ratio") else "",
                    f"{ds.get('multivariate_cox_p', ''):.4e}" if ds.get("multivariate_cox_p") else "",
                    "; ".join(ds.get("covariates_used") or []),
                ])
        return output.getvalue()

    def _build_methods_text(self, r: dict) -> str:
        query = r.get("query", "")
        n_analyzed = r.get("n_datasets_analyzed", 0)
        n_survival = r.get("n_datasets_with_survival", 0)
        n_genes = len(r.get("common_genes", []))
        timestamp = r.get("timestamp", datetime.utcnow().isoformat())

        return f"""METHODS — GEO Survival Analysis
(Edit this text before submission. Fill in [PLACEHOLDERS].)

We searched NCBI GEO (Gene Expression Omnibus; https://www.ncbi.nlm.nih.gov/geo/) for datasets
matching "{query}" and identified {n_analyzed} datasets. Of these, {n_survival} contained
survival outcome data (overall survival or disease-free survival) suitable for analysis.

Gene expression was stratified into high- and low-expression groups using median expression as
the cutoff threshold. Survival analysis was performed using Cox proportional hazards regression
as implemented in the lifelines library (v0.29+) for Python [CITATION]. Kaplan-Meier curves
were generated for visualization. Genes were considered significant at p < 0.05 (Cox regression).
The hazard ratio (HR) and 95% confidence interval (CI) were reported for each dataset.

Cross-dataset meta-analysis was performed across {n_survival} independent cohorts. Heterogeneity
was assessed using Cochran's Q statistic and I² index. Results represent the pooled effect across
all analyzed datasets.

Analysis was performed using GEO Survival Analysis [URL] on {timestamp[:10]}.
[Zenodo DOI: PLACEHOLDER — create at https://zenodo.org]

REFERENCES:
Davidson-Pilon, C. et al. (2023). lifelines: survival analysis in Python. Journal of Open
Source Software. https://doi.org/10.21105/joss.01317

Edgar, R., Domrachev, M., & Lash, A. E. (2002). Gene Expression Omnibus: NCBI gene expression
and hybridization array data repository. Nucleic Acids Research, 30(1), 207-210.
"""

    def _build_params_json(self, r: dict) -> str:
        params = {
            "query": r.get("query", ""),
            "n_datasets_analyzed": r.get("n_datasets_analyzed", 0),
            "n_datasets_with_survival": r.get("n_datasets_with_survival", 0),
            "n_genes_found": len(r.get("common_genes", [])),
            "processing_time_seconds": r.get("processing_time"),
            "timestamp": r.get("timestamp", ""),
            "expression_cutoff_method": "median_split",
            "significance_threshold": 0.05,
            "regression_method": "cox_proportional_hazards",
            "library": "lifelines>=0.29.0",
            "tool_version": "1.0.0",
            "result_id": r.get("result_id", ""),
            "ranking_quality_score": r.get("ranking_quality_score"),
        }
        return json.dumps(params, indent=2)


export_service = ExportService()
