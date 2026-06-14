---
name: clinical-positioning
description: Strategic positioning and clinical roadmap for elevating the GEO Survival Analysis app to clinical-grade prognostic decision support for oncologists. Use when discussing competitive positioning vs predictive/CDS tools (OncoKB, cBioPortal, CIViC, GenomOncology), the prognostic-vs-predictive boundary, personalized/stratified medicine framing, oncologist-facing features, or the F16–F23 clinical roadmap.
user-invocable: true
---

# Clinical Positioning — Prognostic Decision Support for Oncologists

Single source of truth for how we position and elevate the app toward clinical use. The README, NAR submission, GTM copy, and feature decisions should all reference this. Researched May 2026.

## 1. Positioning statement

> **"The only tool that mines all of GEO to surface expression biomarkers validated across many independent cohorts, via a no-code AI interface — complementary to mutation-matching clinical decision support."**

We are a **cross-cohort, expression-based, prognostic evidence engine**. We do *not* compete head-on with mutation→therapy tools; we occupy the complementary expression-prognosis niche.

## 2. Prognostic vs predictive (the hard boundary)

These are terms of art in oncology — keep them straight in all copy:

- **Prognostic** = predicts *outcome/survival* regardless of treatment. ← **This is all the app can honestly do.**
- **Predictive** = predicts *response to a specific drug*. ← This is what OncoKB / cBioPortal / CIViC deliver. **We cannot and will not claim it.**

The word "predictive" appears in our materials **only** in the statistical sense (discrimination/validation, e.g. C-index), never as "tells you which drug." Everything is framed as **evidence-grounded prognostic decision support**.

## 3. Three levels of "personalized medicine" (the honest answer)

- **Stratified medicine — yes, the realistic win.** Assign a patient to a high/intermediate/low-risk group via a validated multi-gene signature (Oncotype DX / MammaPrint logic). Delivered by **F17**. Genuinely useful and a real gap vs KMplot/cBioPortal.
- **Prognostic, not predictive — the boundary.** We describe tumor *biology aggressiveness*, not which drug will work.
- **Full per-patient personalization — investigational only.** One sample can't be calibrated against a model trained on another platform, and oncologists rarely have whole-transcriptome input. Confined to **F23**, research-use-only, behind disclaimers.

## 4. Advantages vs predictive (mutation→therapy) applications

Compared to OncoKB, cBioPortal, CIViC, GenomOncology, MEREDITH, xDECIDE — **complementary, not a replacement**:

| Advantage | Us | Predictive apps |
|---|---|---|
| Data breadth | All of GEO (rare cancers, any tissue/organism) | Curated sets (TCGA, OncoKB KB) |
| Validation | Cross-cohort meta-analysis / replication built in | Single-patient KB annotation, no aggregation |
| Signal | Transcriptome-wide expression (often more prognostic) | Mutation/variant-centric only |
| Interface | Natural-language, no-code | Structured variant input / EHR, bioinformatics-heavy |
| Transparency | Shows cohorts, HRs, KM, forest, I² — no black box | Some return opaque recommendations |
| Discovery | Finds novel biomarkers, even cancers absent from OncoKB | Lookup against known annotations only |
| Cost | Public data, open methods, no license | Mostly commercial/proprietary |

**Where they win (keep positioning honest):** drug-response prediction (directly actionable), clinical validation / regulatory clearance, EHR workflow integration. We are prognostic and investigational. Mutations change treatment; prognosis less often does — so expression prognosis is *partly* white space and *partly* lower clinical utility. State both.

## 5. Clinical roadmap F16–F23

Two pillars, three phases. **Build order: predictive depth first → clinician UX → investigational calculator.**

**Phase 1 — Predictive depth (rigor):**
- **F16** *(M)* — Surface multivariate (clinically-adjusted) Cox HRs in the UI. Backend already computes adjusted HR/p + covariates (`survival_analysis_service.py:707-767`); just propagate + display. **Completes existing F13.**
- **F17** *(L, centerpiece)* — Validated multi-gene prognostic **signature**: continuous Cox risk score (NOT median-split) trained on one cohort, **validated on independent GEO cohorts** with **Harrell's C-index** (`lifelines.utils.concordance_index`, no new dep) + risk-tertile KM. New `signature_service.py`, `POST /api/signature`, new "Signature" UI tab.
- **F18** *(M)* — Clinical **nomogram** rendered from Cox coefficients (custom SVG, no heavy dep).
- **F19** *(M)* — Established-signature **concordance** benchmark: gene-overlap/direction vs public Oncotype DX / MammaPrint / PAM50 gene lists (concordance, never coefficient reproduction).

**Phase 2 — Clinician UX (hands-on, simple, attractive):**
- **F20** *(M)* — "Oncologist Mode": curated cancer-type **gallery** of pre-run, instantly-loaded analyses (breast, lung, colorectal, ovarian, gastric); reuses results-persistence + RAG catalog.
- **F21** *(S/M)* — Plain-language interpretation layer: "what does this mean?" tooltips + AI clinician summary grounded in the real `AnalysisResponse` (cites genes/HRs/GSEs).
- **F22** *(M)* — One-page printable clinical **evidence report** (CSS `@media print`, no backend dep) with prominent RUO disclaimer.

**Phase 3 — Investigational (behind disclaimers):**
- **F23** *(L)* — Single-sample risk score, research-use-only. See §6.
- **F24** *(L)* — Treatment context. See §8.

## 6. Patient-prediction architecture (F23)

**Core reframe — you cannot build a KM curve from one patient.** A KM curve is a *population* estimator. The correct flow: load patient → compute risk score from a *locked, pre-validated* signature → assign to a risk group → show *that group's reference curve* with the patient's predicted position. "Predict further behaviour" = predicted t-year survival + risk group, anchored to a measured C-index. Never a bespoke single-patient curve.

**Separate model-building from patient-scoring:**
1. **Build (F17, offline, once per cancer type)** → locked "Prognostic Model" artifact: gene weights + Cox coefficients + reference expression distribution + reference KM per tertile + measured C-index. Version-pinned.
2. **Score (F23, online, instant)** → normalize → dot-product → assign group → render. No per-patient retraining.

**Scoring pipeline:**
1. **Input (decided):** upload a CSV of the tumor's full expression profile → auto-extract signature genes (reuse probe→gene mapping). Plus a **built-in demo patient** (real held-out GEO sample) to try the flow with zero patient data. CSV processed in-memory only, never persisted.
2. **Normalize against the reference** — rank/quantile-map onto the stored reference distribution (single-sample z-score is undefined; rank-against-reference is the only defensible cross-platform method).
3. **Compute risk score** = dot-product with locked coefficients.
4. **Assign risk group** by percentile vs reference (tertile).
5. **Render** = reference KM for the assigned group + predicted 1/3/5-year survival + C-index + uncertainty note.

`POST /api/predict`: input = model_id + patient expression dict; output = risk score, group, percentile, t-year survival, reference-group KM.

## 8. Treatment Context (F24)

**What it is:** After a patient is scored, the app shows survival curves from GEO cohorts where a specific treatment was documented for the patient's cancer type. Example: "In breast cancer cohorts where patients received adjuvant chemotherapy, high-risk patients like yours had 42% 5-year survival."

**The critical positioning boundary:**
- ✅ Correct framing: *"Historical outcomes from GEO cohorts receiving this treatment"*
- ❌ Wrong framing: *"If treated with X, this patient will respond"* — this is PREDICTIVE and we must never say it

**Architecture (prognostic-in-treated-cohorts):**
- One `PrognosticModel` is built per `(cancer_type, treatment)` pair from treatment-labelled GEO queries (e.g., `"breast cancer tamoxifen overall survival"`).
- These are expression-based prognostic signatures estimated on cohorts that happened to receive a specific treatment — not treatment-response models.
- The patient's expression is rank/quantile-normalized onto each treatment cohort's reference and assigned to a risk group.
- The displayed KM curve is the *reference group curve* from that treated cohort, not a bespoke single-patient curve.
- Model IDs: `treatment_{cancer_type}_{slug}`, stored in `platform_mappings/signature_models/`.
- Patient expression is never persisted (same RUO policy as F23).

**Guardrail language (use verbatim in UI):**
> "Shows historical outcomes from GEO cohorts where this treatment was documented. This is not a treatment recommendation or prediction of treatment response. Research use only."

**Endpoint:** `POST /api/treatment-context` — input: `{cancer_type, expression, clinical?}`; output: list of `TreatmentComparison` (one per treatment, with KM curves and risk group for the patient's risk level in that treated cohort).

## 7. Guardrails (design constraints, not footnotes)

1. **Prognostic-not-predictive language** audited across UI, AI summaries, README, reports.
2. **Investigational / RUO framing** wherever a number could read as a clinical verdict — keeps us clear of FDA CDS / EU MDR device territory. UI must never render an output as a clinical decision.
3. **Cross-platform normalization** (rank/z within cohort) is mandatory for any signature scoring; documented as a method limitation.
4. **No PII** in logs or tool/return values; patient expression accepted in-memory only, never persisted.
5. Reuse first: lifelines `CoxPHFitter` + `concordance_index`, existing KM/forest components, results-persistence endpoints, the pydantic-ai agent. Avoid new deps except optional gated `scikit-survival` for time-dependent AUC.
