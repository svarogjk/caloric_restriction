"""
Validated multi-gene prognostic signature service (F17).

Produces a locked `PrognosticModel` artifact (see signature_models.py) that
encodes a continuous Cox risk score — NOT a median split — trained on one
cohort and validated on independent cohorts with Harrell's C-index.

The same artifact is consumed by F18 (nomogram), F19 (concordance benchmark)
and F23 (single-sample scoring), so the math here is the single source of truth.

Key design points (clinical-positioning skill §6, §7):
  * Risk score = linear predictor = sum_g (coef_g * zscore_g). Continuous.
  * Cross-platform normalization is mandatory: each gene is z-scored WITHIN a
    cohort before fitting/scoring. A single patient (F23) cannot be z-scored
    within a cohort of one, so it is rank-mapped against the stored reference
    distribution instead (`score_single_sample`).
  * C-index is computed by passing the NEGATED risk score to
    `concordance_index` (higher risk -> shorter survival).
  * Research use only; patient expression is never persisted or logged.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.models.signature_models import (
    CohortValidation,
    PredictResponse,
    PrognosticModel,
    ReferenceKMCurve,
    SignatureGene,
    SurvivalAtHorizon,
)

logger = logging.getLogger(__name__)

# Imported lazily-friendly at module load; lifelines is already a project dep.
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.utils import concordance_index


# ==================== Pure numeric helpers (unit-tested) ====================

def zscore_columns(matrix: pd.DataFrame, ref_mean: pd.Series, ref_std: pd.Series) -> pd.DataFrame:
    """Z-score each gene (row) using the supplied reference mean/std.

    `matrix` is genes x samples. Returns genes x samples z-scored.
    Guards against zero variance.
    """
    std = ref_std.replace(0, np.nan)
    z = matrix.sub(ref_mean, axis=0).div(std, axis=0)
    return z.fillna(0.0)


def risk_from_zscores(z: pd.DataFrame, coefficients: pd.Series) -> pd.Series:
    """Continuous risk score per sample = sum_g coef_g * z_g.

    `z` is genes x samples; `coefficients` indexed by gene. Returns one score
    per sample (index = samples).
    """
    common = [g for g in coefficients.index if g in z.index]
    if not common:
        return pd.Series(0.0, index=z.columns)
    return z.loc[common].mul(coefficients.loc[common], axis=0).sum(axis=0)


def harrell_c_index(times: np.ndarray, risk_scores: np.ndarray, events: np.ndarray) -> float:
    """Harrell's C-index. Higher risk score must mean shorter survival, so we
    pass the negated score to lifelines (which expects higher = longer survival)."""
    try:
        c = concordance_index(times, -np.asarray(risk_scores, dtype=float), events)
        return float(c)
    except (ZeroDivisionError, ValueError) as e:
        logger.warning("C-index computation failed: %s", e)
        return float("nan")


def percentile_of(value: float, sorted_ref: List[float]) -> float:
    """Percentile (0-100) of `value` within a sorted reference vector."""
    arr = np.asarray(sorted_ref, dtype=float)
    if arr.size == 0:
        return 50.0
    rank = float(np.searchsorted(arr, value, side="right"))
    return max(0.0, min(100.0, 100.0 * rank / arr.size))


def _quantile_vector(values: np.ndarray, n: int = 101) -> List[float]:
    """101 evenly spaced quantiles (percentiles 0..100) of `values`."""
    if values.size == 0:
        return [0.0] * n
    qs = np.linspace(0.0, 1.0, n)
    return [float(x) for x in np.quantile(values, qs)]


# ==================== Service ====================

class SignatureService:
    """Builds and scores prognostic signatures. Reuses the orchestrator's
    loader + survival services for the real-data path."""

    MIN_TRAIN_SAMPLES = 20
    MIN_EVENTS = 5
    PENALIZER = 0.1  # ridge — stabilises multi-gene Cox on modest cohorts

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        # Bounded LRU store of built models (also lets F23 score against them).
        from collections import OrderedDict
        self._models: "OrderedDict[str, PrognosticModel]" = OrderedDict()
        self._MODELS_MAX = 20

    # ---------- model store ----------

    def get_model(self, model_id: str) -> Optional[PrognosticModel]:
        if model_id in self._models:
            self._models.move_to_end(model_id)
            return self._models[model_id]
        return None

    def _put_model(self, model: PrognosticModel) -> None:
        self._models[model.model_id] = model
        self._models.move_to_end(model.model_id)
        if len(self._models) > self._MODELS_MAX:
            self._models.popitem(last=False)

    # ---------- core builder (cohort dict -> locked model) ----------

    def _build_from_cohorts(
        self,
        query: str,
        cohorts: List[Tuple[str, pd.DataFrame, pd.DataFrame]],
        time_unit: str,
        is_demo: bool,
        cancer_type: Optional[str] = None,
    ) -> PrognosticModel:
        """Fit on the largest cohort, validate on the rest.

        Each cohort tuple is (accession, gene_matrix [genes x samples],
        survival_df [index=samples, cols: time,event]).
        """
        if not cohorts:
            raise ValueError("No usable cohorts for signature building")

        # Largest = training.
        cohorts = sorted(cohorts, key=lambda c: c[1].shape[1], reverse=True)
        train_acc, train_expr, train_surv = cohorts[0]
        val_cohorts = cohorts[1:]

        genes = list(train_expr.index)
        ref_mean = train_expr.mean(axis=1)
        ref_std = train_expr.std(axis=1, ddof=0)

        # Z-score training expression within cohort.
        z_train = zscore_columns(train_expr, ref_mean, ref_std)

        # Fit multivariate Cox on z-scored genes (ridge-penalised).
        fit_df = z_train.T.copy()
        fit_df["time"] = train_surv["time"].reindex(fit_df.index)
        fit_df["event"] = train_surv["event"].reindex(fit_df.index)
        fit_df = fit_df.dropna()
        if len(fit_df) < self.MIN_TRAIN_SAMPLES or fit_df["event"].sum() < self.MIN_EVENTS:
            raise ValueError(
                f"Training cohort {train_acc} too small "
                f"(n={len(fit_df)}, events={int(fit_df['event'].sum())})"
            )

        cph = CoxPHFitter(penalizer=self.PENALIZER)
        cph.fit(fit_df, duration_col="time", event_col="event")
        coefficients = cph.params_  # indexed by gene
        coef_series = pd.Series({g: float(coefficients.get(g, 0.0)) for g in genes})

        # Training risk scores + tertiles.
        train_risk = risk_from_zscores(z_train, coef_series)
        t1, t2 = np.quantile(train_risk.values, [1 / 3, 2 / 3])
        risk_quantiles = _quantile_vector(train_risk.values)

        # Reference KM per tertile (training cohort).
        groups = self._assign_groups(train_risk.values, (float(t1), float(t2)))
        reference_km = self._reference_km_per_group(train_surv, train_risk.index, groups)

        # Per-gene signature entries with reference distributions.
        sig_genes: List[SignatureGene] = []
        for g in genes:
            sig_genes.append(
                SignatureGene(
                    gene_symbol=g,
                    coefficient=float(coef_series[g]),
                    hazard_ratio=float(np.exp(coef_series[g])),
                    ref_mean=float(ref_mean[g]),
                    ref_std=float(ref_std[g]) if ref_std[g] > 0 else 1.0,
                    ref_quantiles=_quantile_vector(train_expr.loc[g].values),
                )
            )

        # Training C-index.
        train_c = harrell_c_index(
            train_surv["time"].reindex(train_risk.index).values,
            train_risk.values,
            train_surv["event"].reindex(train_risk.index).values,
        )
        validations: List[CohortValidation] = [
            CohortValidation(
                accession=train_acc,
                role="training",
                n_samples=int(len(train_risk)),
                n_events=int(train_surv["event"].reindex(train_risk.index).sum()),
                c_index=train_c,
            )
        ]

        # Validate on independent cohorts: z-score WITHIN each cohort, apply
        # the locked coefficients, compute C-index.
        weighted_c, total_w = 0.0, 0
        for acc, expr, surv in val_cohorts:
            shared = [g for g in genes if g in expr.index]
            if len(shared) < 2:
                continue
            v_mean = expr.loc[shared].mean(axis=1)
            v_std = expr.loc[shared].std(axis=1, ddof=0)
            z_val = zscore_columns(expr.loc[shared], v_mean, v_std)
            v_risk = risk_from_zscores(z_val, coef_series.loc[shared])
            aligned = surv.reindex(v_risk.index).dropna()
            if len(aligned) < 10 or aligned["event"].sum() < self.MIN_EVENTS:
                continue
            v_c = harrell_c_index(
                aligned["time"].values,
                v_risk.reindex(aligned.index).values,
                aligned["event"].values,
            )
            if np.isnan(v_c):
                continue
            validations.append(
                CohortValidation(
                    accession=acc,
                    role="validation",
                    n_samples=int(len(aligned)),
                    n_events=int(aligned["event"].sum()),
                    c_index=v_c,
                )
            )
            weighted_c += v_c * len(aligned)
            total_w += len(aligned)

        pooled_c = (weighted_c / total_w) if total_w > 0 else train_c

        model = PrognosticModel(
            model_id=f"sig_{uuid.uuid4().hex[:12]}",
            query=query,
            cancer_type=cancer_type,
            created_at=datetime.now(timezone.utc).isoformat(),
            time_unit=time_unit,
            genes=sig_genes,
            risk_score_tertiles=[float(t1), float(t2)],
            risk_score_quantiles=risk_quantiles,
            reference_km=reference_km,
            training_accession=train_acc,
            n_training_samples=int(len(train_risk)),
            cohort_validations=validations,
            pooled_c_index=float(pooled_c),
            is_demo=is_demo,
        )
        self._put_model(model)
        return model

    @staticmethod
    def _assign_groups(risk: np.ndarray, tertiles: Tuple[float, float]) -> np.ndarray:
        t1, t2 = tertiles
        out = np.full(risk.shape, "intermediate", dtype=object)
        out[risk <= t1] = "low"
        out[risk > t2] = "high"
        return out

    @staticmethod
    def _reference_km_per_group(
        surv: pd.DataFrame, sample_index: pd.Index, groups: np.ndarray
    ) -> List[ReferenceKMCurve]:
        curves: List[ReferenceKMCurve] = []
        group_series = pd.Series(groups, index=sample_index)
        for grp in ("low", "intermediate", "high"):
            members = group_series[group_series == grp].index
            sub = surv.reindex(members).dropna()
            if len(sub) < 3:
                curves.append(
                    ReferenceKMCurve(
                        group=grp, times=[], survival_probabilities=[],
                        n_samples=int(len(sub)), n_events=int(sub["event"].sum()) if len(sub) else 0,
                    )
                )
                continue
            kmf = KaplanMeierFitter()
            kmf.fit(sub["time"], event_observed=sub["event"])
            curves.append(
                ReferenceKMCurve(
                    group=grp,
                    times=[float(t) for t in kmf.survival_function_.index.tolist()],
                    survival_probabilities=[
                        float(p) for p in kmf.survival_function_["KM_estimate"].tolist()
                    ],
                    n_samples=int(len(sub)),
                    n_events=int(sub["event"].sum()),
                )
            )
        return curves

    # ---------- F23: single-sample scoring ----------

    def score_single_sample(
        self, model: PrognosticModel, expression: Dict[str, float]
    ) -> PredictResponse:
        """Score ONE tumour sample against a locked model.

        Single samples cannot be z-scored within a cohort, so each gene value is
        rank-mapped against the stored reference distribution and converted to a
        standard-normal z (the same scale the within-cohort z-scores occupy).
        """
        from scipy.stats import norm

        used = 0
        risk = 0.0
        for g in model.genes:
            if g.gene_symbol not in expression:
                continue
            raw = float(expression[g.gene_symbol])
            pct = percentile_of(raw, g.ref_quantiles) / 100.0
            pct = min(0.995, max(0.005, pct))
            z = float(norm.ppf(pct))
            risk += g.coefficient * z
            used += 1

        tertiles = (model.risk_score_tertiles[0], model.risk_score_tertiles[1])
        group = str(self._assign_groups(np.array([risk]), tertiles)[0])
        risk_pct = percentile_of(risk, model.risk_score_quantiles)

        ref = next((c for c in model.reference_km if c.group == group), model.reference_km[0])
        predicted = self._survival_at_horizons(ref, model.time_unit)

        return PredictResponse(
            model_id=model.model_id,
            risk_score=float(risk),
            risk_group=group,
            risk_percentile=float(risk_pct),
            genes_used=used,
            genes_total=len(model.genes),
            reference_km=ref,
            predicted_survival=predicted,
            pooled_c_index=model.pooled_c_index,
        )

    @staticmethod
    def _survival_at_horizons(curve: ReferenceKMCurve, time_unit: str) -> List[SurvivalAtHorizon]:
        per_year = 12.0 if time_unit.lower().startswith("month") else 365.0
        out: List[SurvivalAtHorizon] = []
        if not curve.times:
            return out
        times = np.asarray(curve.times)
        probs = np.asarray(curve.survival_probabilities)
        for years in (1, 3, 5):
            horizon = years * per_year
            if horizon > times.max():
                continue
            idx = np.searchsorted(times, horizon, side="right") - 1
            if idx < 0:
                continue
            out.append(
                SurvivalAtHorizon(
                    horizon_label=f"{years}-year",
                    time=float(horizon),
                    survival_probability=float(probs[idx]),
                )
            )
        return out

    def build_demo_patient(self, model: PrognosticModel) -> Dict[str, float]:
        """A reproducible high-risk-ish demo sample: each gene set near the 70th
        reference percentile. Lets the F23 flow be tried with zero patient data."""
        patient: Dict[str, float] = {}
        for g in model.genes:
            q = g.ref_quantiles
            patient[g.gene_symbol] = float(q[70]) if len(q) > 70 else g.ref_mean
        return patient

    # ---------- demo signature (deterministic, no GEO needed) ----------

    def build_demo_signature(self, max_genes: int = 12) -> PrognosticModel:
        """Synthesise a fully-formed model with a genuine prognostic signal so
        the whole F17/F18/F19/F23 surface is demonstrable offline."""
        rng = np.random.default_rng(42)
        gene_names = [f"DEMOG{i+1}" for i in range(max_genes)]
        true_beta = rng.normal(0, 0.6, size=max_genes)

        def make_cohort(acc: str, n: int, seed: int) -> Tuple[str, pd.DataFrame, pd.DataFrame]:
            r = np.random.default_rng(seed)
            X = r.normal(0, 1, size=(n, max_genes))  # samples x genes
            lp = X @ true_beta
            # Exponential survival; hazard scales with exp(linear predictor).
            base = r.exponential(scale=1.0, size=n)
            t = base / np.exp(lp) * 1000.0  # days-ish
            censor = r.exponential(scale=2000.0, size=n)
            time = np.minimum(t, censor)
            event = (t <= censor).astype(int)
            expr = pd.DataFrame(X.T, index=gene_names, columns=[f"{acc}_s{i}" for i in range(n)])
            surv = pd.DataFrame(
                {"time": time, "event": event}, index=expr.columns
            )
            return acc, expr, surv

        cohorts = [
            make_cohort("GSE_DEMO_TRAIN", 160, 1),
            make_cohort("GSE_DEMO_VAL1", 90, 2),
            make_cohort("GSE_DEMO_VAL2", 70, 3),
        ]
        return self._build_from_cohorts(
            query="Demo prognostic signature (synthetic)",
            cohorts=cohorts,
            time_unit="days",
            is_demo=True,
            cancer_type="demo",
        )

    # ---------- real-data signature from a saved analysis ----------

    async def build_from_result(
        self, result: dict, max_genes: int = 15
    ) -> PrognosticModel:
        """Build a signature from a saved analysis result.

        Reuses the orchestrator's loader to re-load each cohort's cached
        expression matrix, reduces probes -> candidate genes, extracts survival,
        then defers to `_build_from_cohorts`.
        """
        if self.orchestrator is None:
            raise ValueError("Orchestrator unavailable for real-data signature")

        query = result.get("query", "signature")
        common_genes = result.get("common_genes", [])
        if not common_genes:
            raise ValueError("Saved result has no genes to form a signature")

        # Candidate genes: top by n_datasets then avg p-value, must have a symbol.
        ranked = sorted(
            (g for g in common_genes if g.get("gene_symbol")),
            key=lambda g: (-g.get("n_datasets", 0), g.get("avg_cox_p_value", 1.0)),
        )
        candidate_symbols = []
        seen = set()
        for g in ranked:
            sym = g["gene_symbol"].upper()
            if sym not in seen:
                seen.add(sym)
                candidate_symbols.append(sym)
            if len(candidate_symbols) >= max_genes:
                break
        if len(candidate_symbols) < 2:
            raise ValueError("Not enough symbol-mapped genes for a signature")

        # Candidate cohorts: union of datasets across the candidate genes.
        accessions = set()
        for g in ranked[: max_genes * 2]:
            for ds in g.get("datasets", []):
                accessions.add(ds)

        cohorts: List[Tuple[str, pd.DataFrame, pd.DataFrame]] = []
        time_unit = "days"
        for acc in accessions:
            loaded = await self._reload_cohort(acc)
            if loaded is None:
                continue
            built = await self._cohort_to_gene_survival(loaded, candidate_symbols)
            if built is None:
                continue
            gene_matrix, surv, unit = built
            time_unit = unit or time_unit
            if gene_matrix.shape[0] >= 2 and gene_matrix.shape[1] >= 10:
                cohorts.append((acc, gene_matrix, surv))

        if not cohorts:
            raise ValueError(
                "No cohorts could be re-loaded for signature building "
                "(expression matrices not cached locally)"
            )

        return self._build_from_cohorts(
            query=query, cohorts=cohorts, time_unit=time_unit, is_demo=False,
            cancer_type=None,
        )

    async def _reload_cohort(self, accession: str):
        """Re-load a cohort's cached expression matrix via the loader service."""
        from app.services.geo_client import GEODataset

        loader = self.orchestrator.loader_service
        path = loader.DATASETS_DIR / f"{accession}.parquet"
        if not path.exists():
            logger.info("Cohort %s not cached locally; skipping for signature", accession)
            return None
        ds = GEODataset(
            accession=accession, title=accession, summary="", organism="",
            submission_date="", last_update="", sample_count=0,
            dataset_type="", platforms=[],
        )
        try:
            return await loader.load_dataset(dataset=ds, use_cache=True, normalize=True)
        except (OSError, ValueError, KeyError) as e:
            logger.warning("Failed to reload cohort %s: %s", accession, e)
            return None

    async def _cohort_to_gene_survival(
        self, loaded, candidate_symbols: List[str]
    ) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, Optional[str]]]:
        """Reduce a loaded cohort to (gene_matrix, survival_df, time_unit) for
        the candidate genes only. Aggregates probes -> gene by mean."""
        survival_service = self.orchestrator.survival_service
        if loaded.expression_matrix is None or loaded.sample_metadata is None:
            return None

        # Detect survival columns (LLM then regex fallback).
        detection = survival_service.detect_survival_data_regex(loaded)
        if detection is None or not detection.has_survival_data:
            return None
        time_col = (detection.survival_time_column or "").split(",")[0].strip()
        event_col = (detection.event_column or "").split(",")[0].strip()
        if not time_col or not event_col:
            return None
        try:
            surv = survival_service._extract_survival_data(loaded, time_col, event_col)
        except (ValueError, KeyError):
            return None
        if surv is None or len(surv) < 10:
            return None

        # Probe -> gene symbol aggregation, restricted to candidate genes.
        mapping = loaded.probe_to_gene_mapping or {}
        target = set(candidate_symbols)
        expr = loaded.expression_matrix
        rows: Dict[str, List[str]] = {}
        for probe in expr.index:
            sym = (mapping.get(probe) or "").upper()
            if sym in target:
                rows.setdefault(sym, []).append(probe)
        if not rows:
            return None
        gene_matrix = pd.DataFrame(
            {sym: expr.loc[probes].mean(axis=0) for sym, probes in rows.items()}
        ).T  # genes x samples

        # Align samples.
        common = [s for s in gene_matrix.columns if s in surv.index]
        if len(common) < 10:
            return None
        gene_matrix = gene_matrix[common]
        surv = surv.loc[common]
        return gene_matrix, surv, detection.survival_time_unit
