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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.models.signature_models import (
    ClinicalCovariate,
    CohortValidation,
    PredictResponse,
    PrognosticModel,
    ReferenceKMCurve,
    RiskContribution,
    SignatureGene,
    SurvivalAtHorizon,
    TreatmentArmKM,
)
from app.services.covariate_utils import coerce_numeric, select_usable_covariates
from app.services.survival_analysis_service import _arm_label_matches_drug

logger = logging.getLogger(__name__)

# Imported lazily-friendly at module load; lifelines is already a project dep.
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.exceptions import ConvergenceError
from lifelines.utils import concordance_index

# Combined-model fitting failures we tolerate (fall back to expression-only).
_COX_FIT_ERRORS = (ConvergenceError, ValueError, KeyError, ZeroDivisionError, np.linalg.LinAlgError)


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


def _humanize(name: str) -> str:
    """Turn a metadata column name into a form label, e.g. 'age_at_dx' -> 'Age At Dx'."""
    return name.replace("_", " ").replace(".", " ").strip().title() or name


def covariate_form_spec(model: PrognosticModel) -> List[dict]:
    """Lightweight covariate descriptors that drive the patient-intake form
    (labels, kinds, options — no coefficients). Shared by the gallery and the
    personalize endpoint."""
    return [
        {
            "name": cov.name,
            "display_label": cov.display_label,
            "kind": cov.kind,
            "options": cov.options,
            "min_value": cov.min_value,
            "max_value": cov.max_value,
            "required": cov.required,
        }
        for cov in model.clinical_covariates
    ]


def quantile_normalize_to_reference(
    profile: Dict[str, float], ref_sorted: List[float]
) -> Dict[str, float]:
    """Map a single sample's expression profile onto a reference pooled
    distribution by within-sample rank.

    This is the defensible cross-platform single-sample method: it puts the
    patient's values on the reference's scale (so a raw value's platform/units no
    longer matter) while preserving the sample's relative gene ordering. Returns
    gene -> value in reference units. Needs a reasonably full profile to be
    meaningful (see `_QN_MIN_GENES`)."""
    genes = list(profile.keys())
    if not genes or not ref_sorted:
        return dict(profile)
    vals = np.array([profile[g] for g in genes], dtype=float)
    order = vals.argsort()
    ranks = np.empty(len(vals), dtype=float)
    ranks[order] = np.arange(len(vals))
    pct = ranks / max(1, len(vals) - 1)            # within-sample percentile 0..1
    ref = np.asarray(ref_sorted, dtype=float)
    idx = np.clip((pct * (len(ref) - 1)).round().astype(int), 0, len(ref) - 1)
    mapped = ref[idx]
    return {g: float(mapped[i]) for i, g in enumerate(genes)}


# ==================== Service ====================

class SignatureService:
    """Builds and scores prognostic signatures. Reuses the orchestrator's
    loader + survival services for the real-data path."""

    MIN_TRAIN_SAMPLES = 20
    MIN_EVENTS = 5
    PENALIZER = 0.1  # ridge — stabilises multi-gene Cox on modest cohorts
    # A single sample needs at least this many genes for cross-platform quantile
    # normalization to be meaningful; below it we fall back to per-gene ranking.
    _QN_MIN_GENES = 40
    _LOW_COVERAGE_FRAC = 0.6  # warn below this fraction of signature genes matched

    # Curated Oncologist-Mode models are persisted here as JSON so they survive
    # restarts and LRU eviction (project convention: small caches under backend/,
    # never /tmp). parents[2] of .../backend/app/services/signature_service.py = backend/.
    _MODELS_DIR = Path(__file__).resolve().parents[2] / "platform_mappings" / "signature_models"

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        # Bounded LRU store of built models (also lets F23 score against them).
        from collections import OrderedDict
        self._models: "OrderedDict[str, PrognosticModel]" = OrderedDict()
        self._MODELS_MAX = 20
        # Pinned model ids are exempt from LRU eviction (curated, persisted).
        self._pinned: set[str] = set()
        # result_id -> model_id, so personalizing the same analysis reuses one
        # auto-built signature instead of rebuilding per patient.
        self._result_models: dict[str, str] = {}

    # ---------- model store ----------

    def get_model(self, model_id: str) -> Optional[PrognosticModel]:
        if model_id in self._models:
            self._models.move_to_end(model_id)
            return self._models[model_id]
        # Fall back to a persisted curated model (survives eviction / restart).
        loaded = self._load_one_from_disk(model_id)
        if loaded is not None:
            self._put_model(loaded, pin=True)
            return loaded
        return None

    def _put_model(self, model: PrognosticModel, pin: bool = False) -> None:
        self._models[model.model_id] = model
        self._models.move_to_end(model.model_id)
        if pin:
            self._pinned.add(model.model_id)
        if len(self._models) > self._MODELS_MAX:
            # Evict the oldest NON-pinned model.
            for key in list(self._models.keys()):
                if key not in self._pinned:
                    del self._models[key]
                    break

    # ---------- durable persistence (curated models only) ----------

    def save_model_to_disk(self, model: PrognosticModel) -> None:
        """Persist a curated model and pin it in memory."""
        self._MODELS_DIR.mkdir(parents=True, exist_ok=True)
        path = self._MODELS_DIR / f"{model.model_id}.json"
        path.write_text(model.model_dump_json())
        self._put_model(model, pin=True)

    def _load_one_from_disk(self, model_id: str) -> Optional[PrognosticModel]:
        path = self._MODELS_DIR / f"{model_id}.json"
        if not path.exists():
            return None
        try:
            return PrognosticModel.model_validate_json(path.read_text())
        except (OSError, ValueError) as e:
            logger.warning("Failed to load persisted model %s: %s", model_id, e)
            return None

    def load_persisted_models(self) -> int:
        """Load every persisted curated model into memory (pinned). Called at
        startup. Returns the number loaded."""
        if not self._MODELS_DIR.exists():
            return 0
        count = 0
        for path in self._MODELS_DIR.glob("*.json"):
            try:
                model = PrognosticModel.model_validate_json(path.read_text())
            except (OSError, ValueError) as e:
                logger.warning("Skipping unreadable persisted model %s: %s", path.name, e)
                continue
            self._put_model(model, pin=True)
            count += 1
        if count:
            logger.info("Loaded %d persisted prognostic model(s)", count)
        return count

    def find_model_by_cancer(self, cancer_type: str) -> Optional[PrognosticModel]:
        """Return a loaded/persisted model tagged with this cancer type, if any."""
        for model in self._models.values():
            if (model.cancer_type or "").lower() == cancer_type.lower():
                return model
        return None

    # ---------- core builder (cohort dict -> locked model) ----------

    def _build_from_cohorts(
        self,
        query: str,
        cohorts: List[Tuple[str, pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]],
        time_unit: str,
        is_demo: bool,
        cancer_type: Optional[str] = None,
    ) -> PrognosticModel:
        """Fit on the largest cohort, validate on the rest.

        Each cohort tuple is (accession, gene_matrix [genes x samples],
        survival_df [index=samples, cols: time,event], clinical_df or None
        [index=samples, cols: covariate values]). When the training cohort
        carries usable clinical covariates a combined clinical+expression model
        is also fitted; otherwise the model is expression-only.
        """
        if not cohorts:
            raise ValueError("No usable cohorts for signature building")

        # Largest = training.
        cohorts = sorted(cohorts, key=lambda c: c[1].shape[1], reverse=True)
        train_acc, train_expr, train_surv, train_clinical = cohorts[0]
        val_cohorts = cohorts[1:]

        genes = list(train_expr.index)
        ref_mean = train_expr.mean(axis=1)
        ref_std = train_expr.std(axis=1, ddof=0)

        # Pooled distribution of all training expression values — the reference
        # for cross-platform single-sample quantile normalization at score time.
        pooled = train_expr.to_numpy().ravel()
        pooled = pooled[np.isfinite(pooled)]
        reference_pooled_quantiles = _quantile_vector(pooled, n=256)

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
        # the locked coefficients, compute C-index. Also retain per-cohort
        # expression risk + clinical data for the combined-model validation.
        weighted_c, total_w = 0.0, 0
        val_collected: List[Tuple[str, pd.Series, pd.DataFrame, Optional[pd.DataFrame]]] = []
        for acc, expr, surv, clin in val_cohorts:
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
            val_collected.append((acc, v_risk.reindex(aligned.index), aligned, clin))

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
            reference_pooled_quantiles=reference_pooled_quantiles,
            training_accession=train_acc,
            n_training_samples=int(len(train_risk)),
            cohort_validations=validations,
            pooled_c_index=float(pooled_c),
            c_index_expression_only=float(pooled_c),
            is_demo=is_demo,
        )

        # Combined clinical + expression model (no-op when no usable covariates).
        self._augment_with_combined(
            model=model,
            train_risk=train_risk,
            train_surv=train_surv,
            train_clinical=train_clinical,
            val_collected=val_collected,
            expression_pooled_c=float(pooled_c),
        )

        self._put_model(model)
        return model

    # ---------- combined clinical + expression model ----------

    def _augment_with_combined(
        self,
        model: PrognosticModel,
        train_risk: pd.Series,
        train_surv: pd.DataFrame,
        train_clinical: Optional[pd.DataFrame],
        val_collected: List[Tuple[str, pd.Series, pd.DataFrame, Optional[pd.DataFrame]]],
        expression_pooled_c: float,
    ) -> None:
        """Fit a combined clinical+expression Cox model and populate the model's
        combined fields IN PLACE. No-op (expression-only) when the training
        cohort has no usable clinical covariates or the fit fails.

        The combined linear predictor is computed with the SAME formula used at
        scoring time (`_combined_linear_predictor`) so train and score agree,
        rather than relying on lifelines' internal mean-centering.
        """
        if train_clinical is None or train_clinical.empty:
            return
        clin = train_clinical.reindex(train_risk.index)
        usable = select_usable_covariates(clin, list(clin.columns))
        if not usable:
            return

        # Build the fit design: 'risk' (raw expression score) + processed covariates.
        design = pd.DataFrame({"risk": train_risk})
        numeric_ref: Dict[str, Tuple[float, float]] = {}
        cat_info: Dict[str, List[str]] = {}  # name -> categories (desc freq; [0] = reference)
        for name in usable:
            numeric = coerce_numeric(clin[name])
            # Treat as continuous only if there are enough distinct values;
            # low-cardinality fields (grade, stage, ER status) are better as
            # categorical dropdowns in the intake form.
            is_numeric = (
                numeric is not None
                and numeric.notna().sum() >= self.MIN_TRAIN_SAMPLES // 2
                and numeric.dropna().nunique() > 5
            )
            if is_numeric:
                mean = float(numeric.mean())
                std = float(numeric.std(ddof=0)) or 1.0
                numeric_ref[name] = (mean, std)
                design[name] = ((numeric - mean) / std)
            else:
                cats = clin[name].astype(str).where(clin[name].notna())
                levels = cats.value_counts().index.tolist()
                if len(levels) < 2 or len(levels) > 8:
                    continue  # constant or too sparse to encode usefully
                cat_info[name] = levels
                design[name] = pd.Categorical(cats, categories=levels)

        cov_names = [c for c in design.columns if c != "risk"]
        if not cov_names:
            return

        # One-hot encode categoricals (drop the most-frequent level = reference).
        cat_cols = list(cat_info.keys())
        encoded = pd.get_dummies(design, columns=cat_cols, drop_first=True) if cat_cols else design.copy()
        encoded = encoded.astype(float)
        encoded["time"] = train_surv["time"].reindex(encoded.index)
        encoded["event"] = train_surv["event"].reindex(encoded.index)
        encoded = encoded.dropna()
        if len(encoded) < self.MIN_TRAIN_SAMPLES or encoded["event"].sum() < self.MIN_EVENTS:
            return

        try:
            cph = CoxPHFitter(penalizer=self.PENALIZER)
            cph.fit(encoded, duration_col="time", event_col="event")
        except _COX_FIT_ERRORS as e:
            logger.warning("Combined clinical+expression fit failed; expression-only: %s", e)
            return

        params = cph.params_
        if "risk" not in params.index:
            return
        beta_risk = float(params["risk"])

        covariates: List[ClinicalCovariate] = []
        for name in numeric_ref:
            mean, std = numeric_ref[name]
            covariates.append(
                ClinicalCovariate(
                    name=name,
                    display_label=_humanize(name),
                    kind="numeric",
                    coefficient=float(params.get(name, 0.0)),
                    ref_mean=mean,
                    ref_std=std,
                    min_value=float(coerce_numeric(clin[name]).min()),
                    max_value=float(coerce_numeric(clin[name]).max()),
                    required=False,
                )
            )
        for name, levels in cat_info.items():
            reference = levels[0]
            cat_coefs = {reference: 0.0}
            for level in levels[1:]:
                cat_coefs[level] = float(params.get(f"{name}_{level}", 0.0))
            covariates.append(
                ClinicalCovariate(
                    name=name,
                    display_label=_humanize(name),
                    kind="categorical",
                    category_coefficients=cat_coefs,
                    reference_category=reference,
                    options=levels,
                    required=False,
                )
            )
        if not covariates:
            return

        # Combined linear predictor on training -> tertiles, quantiles, reference KM.
        train_lp = self._combined_linear_predictor(train_risk, clin, covariates, beta_risk)
        ct1, ct2 = (float(x) for x in np.quantile(train_lp.values, [1 / 3, 2 / 3]))
        combined_groups = self._assign_groups(train_lp.values, (ct1, ct2))
        combined_km = self._reference_km_per_group(train_surv, train_lp.index, combined_groups)

        # Validation discrimination: combined vs clinical-only (cohorts with clinical data).
        c_combined = self._validation_c_index(
            val_collected, covariates, beta_risk, include_expression=True
        )
        c_clinical = self._validation_c_index(
            val_collected, covariates, beta_risk, include_expression=False
        )
        # Fall back to training C-index when no validation cohort carries covariates.
        if c_combined is None:
            c_combined = harrell_c_index(
                train_surv["time"].reindex(train_lp.index).values,
                train_lp.values,
                train_surv["event"].reindex(train_lp.index).values,
            )
        if c_clinical is None:
            clin_only_lp = self._combined_linear_predictor(
                train_risk, clin, covariates, beta_risk, include_expression=False
            )
            c_clinical = harrell_c_index(
                train_surv["time"].reindex(clin_only_lp.index).values,
                clin_only_lp.values,
                train_surv["event"].reindex(clin_only_lp.index).values,
            )

        model.clinical_covariates = covariates
        model.expression_score_coefficient = beta_risk
        model.combined_risk_tertiles = [ct1, ct2]
        model.combined_risk_quantiles = _quantile_vector(train_lp.values)
        model.combined_reference_km = combined_km
        model.c_index_clinical_only = float(c_clinical) if c_clinical is not None else None
        model.c_index_combined = float(c_combined) if c_combined is not None else None
        if c_combined is not None:
            model.delta_c_index = float(c_combined) - expression_pooled_c
            model.pooled_c_index = float(c_combined)  # headline now reflects combined

    def _combined_linear_predictor(
        self,
        risk: pd.Series,
        clinical_df: Optional[pd.DataFrame],
        covariates: List[ClinicalCovariate],
        beta_risk: float,
        include_expression: bool = True,
    ) -> pd.Series:
        """Combined linear predictor = β_risk·expr_risk + Σ covariate contributions.
        Missing covariates / values contribute 0 (graceful)."""
        lp = pd.Series(0.0, index=risk.index)
        if include_expression:
            lp = lp.add(beta_risk * risk, fill_value=0.0)
        if clinical_df is None:
            return lp
        cdf = clinical_df.reindex(risk.index)
        for cov in covariates:
            if cov.name not in cdf.columns:
                continue
            col = cdf[cov.name]
            if cov.kind == "numeric":
                num = pd.to_numeric(col, errors="coerce")
                contrib = cov.coefficient * (num - cov.ref_mean) / (cov.ref_std or 1.0)
            else:
                contrib = col.astype(str).map(
                    lambda v: cov.category_coefficients.get(v, 0.0)
                )
                contrib = pd.to_numeric(contrib, errors="coerce")
            lp = lp.add(contrib.fillna(0.0), fill_value=0.0)
        return lp

    def _validation_c_index(
        self,
        val_collected: List[Tuple[str, pd.Series, pd.DataFrame, Optional[pd.DataFrame]]],
        covariates: List[ClinicalCovariate],
        beta_risk: float,
        include_expression: bool,
    ) -> Optional[float]:
        """Sample-weighted C-index of the combined (or clinical-only) score across
        validation cohorts that carry the clinical covariates. None if none do."""
        weighted, total = 0.0, 0
        cov_names = {c.name for c in covariates}
        for _acc, v_risk, aligned_surv, clin in val_collected:
            if clin is None:
                continue
            if not cov_names.intersection(set(clin.columns)):
                continue
            lp = self._combined_linear_predictor(
                v_risk, clin, covariates, beta_risk, include_expression=include_expression
            )
            c = harrell_c_index(
                aligned_surv["time"].reindex(lp.index).values,
                lp.values,
                aligned_surv["event"].reindex(lp.index).values,
            )
            if np.isnan(c):
                continue
            weighted += c * len(lp)
            total += len(lp)
        return (weighted / total) if total > 0 else None

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
        self,
        model: PrognosticModel,
        expression: Dict[str, float],
        clinical: Optional[Dict[str, object]] = None,
    ) -> PredictResponse:
        """Score ONE tumour sample against a locked model.

        Cross-platform normalization (the statistically critical step): when a
        reasonably full profile is supplied we quantile-normalize it onto the
        model's reference pooled distribution (platform-independent); with sparse
        input we fall back to per-gene ranking, which assumes the input is on a
        comparable expression scale and is flagged in `warnings`/`normalization`.

        When the model carries clinical covariates AND the caller supplies any of
        them, the sample is scored on the COMBINED linear predictor against the
        combined reference distribution; otherwise it falls back to the
        expression-only score (flagged in `scored_on`).
        """
        from scipy.stats import norm

        warnings_out: List[str] = []

        # --- Expression normalization onto the reference scale ---
        profile_size = len(expression)
        if model.reference_pooled_quantiles and profile_size >= self._QN_MIN_GENES:
            scored_expr = quantile_normalize_to_reference(
                {k: float(v) for k, v in expression.items()}, model.reference_pooled_quantiles
            )
            normalization = "quantile-normalized to reference distribution (cross-platform)"
        else:
            scored_expr = {k: float(v) for k, v in expression.items()}
            normalization = "per-gene rank vs reference (assumes a comparable expression scale)"
            if model.reference_pooled_quantiles:
                warnings_out.append(
                    f"Only {profile_size} genes provided. Cross-platform quantile normalization "
                    f"needs a fuller tumour profile (≥{self._QN_MIN_GENES} genes); scored by "
                    "per-gene rank instead, which assumes the input is on a comparable expression "
                    "scale to the reference cohort."
                )
                # Scale-mismatch heuristic: do the raw values sit inside the reference range?
                ref_lo = model.reference_pooled_quantiles[0]
                ref_hi = model.reference_pooled_quantiles[-1]
                vals = [float(v) for v in expression.values()]
                if vals and ref_hi > ref_lo:
                    frac_out = sum(1 for v in vals if v < ref_lo or v > ref_hi) / len(vals)
                    if frac_out > 0.5:
                        warnings_out.append(
                            "Most input values fall outside the reference expression range — the "
                            "assay scale looks different from the training platform, so this score "
                            "may be unreliable. Provide a full profile for proper normalization."
                        )

        used = 0
        expr_risk = 0.0
        for g in model.genes:
            if g.gene_symbol not in scored_expr:
                continue
            raw = scored_expr[g.gene_symbol]
            pct = percentile_of(raw, g.ref_quantiles) / 100.0
            pct = min(0.995, max(0.005, pct))
            z = float(norm.ppf(pct))
            expr_risk += g.coefficient * z
            used += 1

        if used < len(model.genes) and used / max(1, len(model.genes)) < self._LOW_COVERAGE_FRAC:
            warnings_out.append(
                f"Only {used}/{len(model.genes)} signature genes were found in the input; the risk "
                "estimate is less reliable with low signature coverage."
            )

        contributions: List[RiskContribution] = []

        # Decide combined vs expression-only.
        supplied = {k: v for k, v in (clinical or {}).items() if v not in (None, "")}
        use_combined = bool(
            model.clinical_covariates
            and model.combined_reference_km
            and supplied
            and any(cov.name in supplied for cov in model.clinical_covariates)
        )

        if use_combined:
            score = model.expression_score_coefficient * expr_risk
            contributions.append(
                RiskContribution(
                    label="Expression signature",
                    contribution=float(score),
                    kind="expression",
                )
            )
            for cov in model.clinical_covariates:
                if cov.name not in supplied:
                    continue
                raw_val = supplied[cov.name]
                if cov.kind == "numeric":
                    try:
                        val = float(raw_val)
                    except (TypeError, ValueError):
                        warnings_out.append(
                            f"{cov.display_label} value '{raw_val}' is not numeric; ignored."
                        )
                        continue
                    if (
                        cov.min_value is not None and cov.max_value is not None
                        and (val < cov.min_value or val > cov.max_value)
                    ):
                        warnings_out.append(
                            f"{cov.display_label}={val:g} is outside the training range "
                            f"({cov.min_value:g}–{cov.max_value:g}); extrapolating."
                        )
                    contrib = cov.coefficient * (val - cov.ref_mean) / (cov.ref_std or 1.0)
                    label = f"{cov.display_label} = {val:g}"
                else:
                    level = str(raw_val)
                    if level not in cov.category_coefficients:
                        warnings_out.append(
                            f"{cov.display_label} value '{level}' was not seen in training "
                            f"(known: {', '.join(cov.options or [])}); contributed 0."
                        )
                    contrib = cov.category_coefficients.get(level, 0.0)
                    label = f"{cov.display_label} = {level}"
                score += float(contrib)
                contributions.append(
                    RiskContribution(label=label, contribution=float(contrib), kind="clinical")
                )
            tertiles = (model.combined_risk_tertiles[0], model.combined_risk_tertiles[1])
            quantiles = model.combined_risk_quantiles or model.risk_score_quantiles
            km_set = model.combined_reference_km
            scored_on = "combined"
        else:
            score = expr_risk
            contributions.append(
                RiskContribution(
                    label="Expression signature", contribution=float(expr_risk), kind="expression"
                )
            )
            tertiles = (model.risk_score_tertiles[0], model.risk_score_tertiles[1])
            quantiles = model.risk_score_quantiles
            km_set = model.reference_km
            scored_on = (
                "expression-only (clinical omitted)"
                if model.clinical_covariates
                else "expression-only"
            )

        group = str(self._assign_groups(np.array([score]), tertiles)[0])
        risk_pct = percentile_of(score, quantiles)
        ref = next((c for c in km_set if c.group == group), km_set[0])
        predicted = self._survival_at_horizons(ref, model.time_unit)

        return PredictResponse(
            model_id=model.model_id,
            risk_score=float(score),
            risk_group=group,
            risk_percentile=float(risk_pct),
            genes_used=used,
            genes_total=len(model.genes),
            reference_km=ref,
            predicted_survival=predicted,
            pooled_c_index=model.pooled_c_index,
            scored_on=scored_on,
            normalization=normalization,
            warnings=warnings_out,
            contributions=contributions,
            c_index_expression_only=model.c_index_expression_only,
            c_index_clinical_only=model.c_index_clinical_only,
            c_index_combined=model.c_index_combined,
            delta_c_index=model.delta_c_index,
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

    def build_demo_signature(
        self,
        max_genes: int = 12,
        query: str = "Demo risk signature (synthetic)",
        cancer_type: str = "demo",
    ) -> PrognosticModel:
        """Synthesise a fully-formed model with a genuine prognostic signal so
        the whole F17/F18/F19/F23 surface is demonstrable offline. Includes
        synthetic clinical covariates (age, grade) that truly affect survival,
        so the combined clinical+expression path is exercised without GEO data."""
        rng = np.random.default_rng(42)
        # Real cancer gene symbols (synthetic coefficients) so the demo exercises
        # the realistic surfaces — therapy-evidence lookup and the landing sample
        # patient both resolve. The model stays clearly labelled is_demo=True.
        _DEMO_GENES = [
            "TP53", "MKI67", "ESR1", "ERBB2", "EGFR", "KRAS", "MYC", "PTEN",
            "CCND1", "RB1", "AKT1", "PIK3CA", "BCL2", "VEGFA", "CD44", "TOP2A",
            "AURKA", "BIRC5", "FOXM1", "STAT3", "CDK1", "CCNB1", "MMP9", "CD8A",
        ]
        gene_names = (_DEMO_GENES + [f"DEMOG{i+1}" for i in range(max_genes)])[:max_genes]
        true_beta = rng.normal(0, 0.6, size=max_genes)
        age_beta = 0.025           # per year above mean
        grade_beta = {"1": -0.4, "2": 0.0, "3": 0.6}  # higher grade -> higher risk

        def make_cohort(
            acc: str, n: int, seed: int
        ) -> Tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            r = np.random.default_rng(seed)
            X = r.normal(0, 1, size=(n, max_genes))  # samples x genes
            ages = r.normal(62, 10, size=n).clip(30, 90)
            grades = r.choice(["1", "2", "3"], size=n, p=[0.3, 0.4, 0.3])
            lp = (
                X @ true_beta
                + age_beta * (ages - 62)
                + np.array([grade_beta[g] for g in grades])
            )
            # Exponential survival; hazard scales with exp(linear predictor).
            base = r.exponential(scale=1.0, size=n)
            t = base / np.exp(lp) * 1000.0  # days-ish
            censor = r.exponential(scale=2000.0, size=n)
            time = np.minimum(t, censor)
            event = (t <= censor).astype(int)
            cols = [f"{acc}_s{i}" for i in range(n)]
            expr = pd.DataFrame(X.T, index=gene_names, columns=cols)
            surv = pd.DataFrame({"time": time, "event": event}, index=cols)
            clinical = pd.DataFrame({"age": ages, "grade": grades}, index=cols)
            return acc, expr, surv, clinical

        cohorts = [
            make_cohort("GSE_DEMO_TRAIN", 160, 1),
            make_cohort("GSE_DEMO_VAL1", 90, 2),
            make_cohort("GSE_DEMO_VAL2", 70, 3),
        ]
        return self._build_from_cohorts(
            query=query,
            cohorts=cohorts,
            time_unit="days",
            is_demo=True,
            cancer_type=cancer_type,
        )

    # ---------- real-data signature from a saved analysis ----------

    async def get_or_build_for_result(
        self, result_id: str, result: dict, max_genes: int = 15,
        cancer_type: Optional[str] = None,
    ) -> PrognosticModel:
        """Return a signature for a saved analysis, building it once and caching
        the result_id -> model_id mapping so later patient scores reuse it.

        This is the auto-build step of the unified flow: attaching patient data to
        any analysis transparently builds (or reuses) its prognostic model."""
        cached_id = self._result_models.get(result_id)
        if cached_id:
            model = self.get_model(cached_id)
            if model is not None:
                return model
        model = await self.build_from_result(result, max_genes=max_genes, cancer_type=cancer_type)
        self._result_models[result_id] = model.model_id
        return model

    async def build_from_result(
        self, result: dict, max_genes: int = 15, cancer_type: Optional[str] = None
    ) -> PrognosticModel:
        """Build a signature from a saved analysis result.

        Reuses the orchestrator's loader to re-load each cohort's cached
        expression matrix, reduces probes -> candidate genes, extracts survival
        and clinical covariates, then defers to `_build_from_cohorts`.
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

        cohorts: List[Tuple[str, pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]] = []
        time_unit = "days"
        for acc in accessions:
            loaded = await self._reload_cohort(acc)
            if loaded is None:
                continue
            built = await self._cohort_to_gene_survival(loaded, candidate_symbols)
            if built is None:
                continue
            gene_matrix, surv, clinical_df, unit = built
            time_unit = unit or time_unit
            if gene_matrix.shape[0] >= 2 and gene_matrix.shape[1] >= 10:
                cohorts.append((acc, gene_matrix, surv, clinical_df))

        if not cohorts:
            raise ValueError(
                "No cohorts had usable survival data to build a signature for this analysis"
            )

        return self._build_from_cohorts(
            query=query, cohorts=cohorts, time_unit=time_unit, is_demo=False,
            cancer_type=cancer_type,
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
    ) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame], Optional[str]]]:
        """Reduce a loaded cohort to (gene_matrix, survival_df, clinical_df,
        time_unit) for the candidate genes only. Aggregates probes -> gene by
        mean; clinical_df holds detected covariate columns (or None)."""
        survival_service = self.orchestrator.survival_service
        if loaded.expression_matrix is None or loaded.sample_metadata is None:
            return None

        # Detect survival columns (LLM then regex fallback).
        detection = await survival_service.detect_survival_columns(loaded)
        if detection is None:
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

        # Clinical covariates: detected covariate columns restricted to `common`.
        clinical_df: Optional[pd.DataFrame] = None
        metadata = loaded.sample_metadata
        if metadata is not None and not metadata.empty:
            try:
                cov_cols = survival_service._detect_covariate_columns(
                    metadata, exclude={time_col, event_col}
                )
            except (KeyError, ValueError):
                cov_cols = []
            cov_cols = [c for c in cov_cols if c in metadata.columns]
            if cov_cols:
                idx = [s for s in common if s in metadata.index]
                if len(idx) >= 10:
                    clinical_df = metadata.loc[idx, cov_cols]

        return gene_matrix, surv, clinical_df, detection.survival_time_unit

    async def load_cohort_treatment_arms(
        self, accession: str
    ) -> Optional[Tuple[pd.DataFrame, pd.Series, Dict[int, str]]]:
        """Load `accession`'s cached survival data and detect a treatment/arm
        assignment, once — reused across multiple drug-name match attempts
        (`match_treatment_arm_km`) so checking several candidate drugs against
        the same cohort doesn't repeat the LLM-backed column detection call
        per drug.

        Returns (survival_df[time, event], treatment_binary, arm_names) or
        None when the cohort isn't cached locally or has no usable
        survival/treatment columns.
        """
        if self.orchestrator is None:
            return None
        survival_service = self.orchestrator.survival_service

        loaded = await self._reload_cohort(accession)
        if loaded is None or loaded.sample_metadata is None:
            return None

        detection = await survival_service.detect_survival_columns(loaded)
        if detection is None:
            return None
        time_col = (detection.survival_time_column or "").split(",")[0].strip()
        event_col = (detection.event_column or "").split(",")[0].strip()
        if not time_col or not event_col:
            return None
        try:
            surv = survival_service._extract_survival_data(loaded, time_col, event_col)
        except (ValueError, KeyError):
            return None
        if surv is None or len(surv) < 20:
            return None

        metadata = loaded.sample_metadata
        treat_col = survival_service._detect_treatment_column(
            metadata, exclude={time_col, event_col}
        )
        if treat_col is None:
            return None
        binarized = survival_service._binarize_treatment(metadata[treat_col])
        if binarized is None:
            return None
        treatment_binary, arm_names = binarized

        common = [s for s in surv.index if s in treatment_binary.index]
        if len(common) < 20:
            return None
        return surv.loc[common], treatment_binary.loc[common], arm_names

    def match_treatment_arm_km(
        self,
        survival_df: pd.DataFrame,
        treatment_binary: pd.Series,
        arm_names: Dict[int, str],
        drug_name: str,
    ) -> Optional[List[TreatmentArmKM]]:
        """Tier-1 "Treatments to consider" KM evidence, given a cohort already
        loaded via `load_cohort_treatment_arms`: only when the treated arm's
        free-text label actually names `drug_name` does this fit descriptive
        per-arm KM curves (treated vs untreated/control) and return them.

        Gene-independent: a raw survival-by-arm comparison, not an
        expression-conditioned hazard ratio (that's `_fit_interaction_cox`,
        used elsewhere for the predictive-biomarker forest). Never fabricates
        an attribution — returns None when the arm label doesn't match.
        """
        if self.orchestrator is None:
            return None
        if not _arm_label_matches_drug(arm_names.get(1, ""), drug_name):
            return None
        arms = self.orchestrator.survival_service._fit_treatment_arm_km(
            survival_df["time"], survival_df["event"], treatment_binary, arm_names
        )
        if arms is None:
            return None
        return [TreatmentArmKM(**arm) for arm in arms]
