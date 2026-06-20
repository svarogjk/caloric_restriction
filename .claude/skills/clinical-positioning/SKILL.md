---
name: clinical-positioning
description: Strategic positioning and clinical roadmap for the GEO Survival Analysis app as a predictive biomarker discovery + advisory treatment-guidance tool for oncologists. Use when discussing competitive positioning vs companion-diagnostic / CDS tools (OncoKB, cBioPortal, CIViC, GenomOncology), the predictive-biomarker vs companion-diagnostic boundary, advisory treatment-recommendation framing, personalized/stratified medicine framing, oncologist-facing features, or the F16–F24 clinical roadmap.
user-invocable: true
---

# Clinical Positioning — Predictive Biomarkers & Advisory Treatment Guidance

Single source of truth for how we position the app. The README, NAR submission,
GTM copy, UI strings, and LLM prompts should all match this. Repositioned to
**predictive** June 2026.

## 1. Positioning statement

> **"The only tool that mines all of GEO to surface treatment-effect-modifying
> (predictive) expression biomarkers validated across independent cohorts — and
> turns a patient's tumour profile into advisory, evidence-grounded treatment
> suggestions — via a no-code AI interface. A research-use information source,
> complementary to companion-diagnostic decision support."**

We are a **cross-cohort, expression-based, predictive biomarker engine** with an
**advisory treatment-guidance** layer. We surface which biomarkers *modify the
effect of treatment* and, for a patient, which treatments are worth discussing —
grounded in GEO outcomes and public biomarker→therapy knowledge bases.

## 2. What "predictive" means here (and what it does NOT)

These are terms of art in oncology — keep them straight in all copy.

**Predictive — what we DO claim, honestly:**
- **Treatment-effect-modifying biomarkers.** The statistical definition of a
  *predictive* biomarker is one whose association with outcome **differs by
  treatment** — tested with a `expression × treatment` interaction term in a Cox
  model. Where a GEO cohort carries a treatment/arm column with enough events, we
  compute per-arm hazard ratios + an interaction p-value and surface genes whose
  effect is treatment-dependent. This is genuinely predictive, not relabeled
  prognosis.
- **Advisory treatment guidance.** For a scored patient we surface *treatments to
  consider/discuss*, grounded in (a) documented biomarker→therapy evidence
  (CIViC / DGIdb) for the patient's risk-driving genes and (b) outcomes from GEO
  cohorts where that treatment was documented. Framed as suggestions for the
  tumour board, always with the source shown.

**NOT predictive — what we never claim:**
- **Not a validated companion diagnostic.** We do not assert "this patient *will*
  respond to drug X." Output is hypothesis-generating and research-use.
- **Not a prescription.** Treatment suggestions are advisory and framed "to
  discuss"; no prescribing/administering imperatives (enforced by the
  `_PRESCRIBING_PATTERN` guardrail in `chat_routes.py`).
- **Not de-novo drug-sensitivity prediction / drug-matching.** We surface
  *documented* associations and *measured* cohort outcomes — we do not invent a
  drug-response model from cell-line data.

Every predictive claim carries a **hypothesis-generating, validate-prospectively**
advisory label. This keeps us an information source, clear of FDA-CDS / EU-MDR
device territory.

## 3. Three levels of "personalized medicine" (the honest answer)

- **Stratified medicine — the realistic win.** Assign a patient to a
  high/intermediate/low-risk group via a validated multi-gene signature (Oncotype
  DX / MammaPrint logic). Delivered by **F17**. A real gap vs KMplot/cBioPortal.
- **Advisory, not directive — the boundary.** We suggest treatments *to discuss*
  with evidence and cohort outcomes attached; we never instruct or guarantee a
  response.
- **Full per-patient personalization — investigational only.** One sample can't be
  calibrated against a model trained on another platform, and oncologists rarely
  have whole-transcriptome input. Confined to **F23**, research-use-only, behind
  advisory disclaimers.

## 4. Advantages vs companion-diagnostic (mutation→therapy) applications

Compared to OncoKB, cBioPortal, CIViC, GenomOncology, MEREDITH, xDECIDE —
**complementary, not a replacement**:

| Advantage | Us | Companion-Dx apps |
|---|---|---|
| Data breadth | All of GEO (rare cancers, any tissue/organism) | Curated sets (TCGA, OncoKB KB) |
| Validation | Cross-cohort meta-analysis / replication built in | Single-patient KB annotation, no aggregation |
| Signal | Transcriptome-wide expression, incl. treatment-effect-modifying biomarkers | Mutation/variant-centric only |
| Treatment guidance | Advisory suggestions grounded in CIViC/DGIdb + GEO cohort outcomes | Curated variant→therapy rules |
| Interface | Natural-language, no-code | Structured variant input / EHR, bioinformatics-heavy |
| Transparency | Shows cohorts, HRs, KM, forest, I², interaction p — no black box | Some return opaque recommendations |
| Discovery | Finds novel predictive biomarkers, even cancers absent from OncoKB | Lookup against known annotations only |
| Cost | Public data, open methods, no license | Mostly commercial/proprietary |

**Where they win (keep positioning honest):** validated drug-response prediction
(directly actionable), clinical validation / regulatory clearance, EHR workflow
integration. We are advisory and research-use. State both.

## 5. Clinical roadmap F16–F24

Two pillars, three phases. **Build order: predictive depth first → clinician UX →
investigational calculator.**

**Phase 1 — Predictive depth (rigor):**
- **F16** *(M)* — Surface multivariate (clinically-adjusted) Cox HRs in the UI.
  Backend already computes adjusted HR/p + covariates
  (`survival_analysis_service.py`); propagate + display. **Completes F13.**
- **F17** *(L, centerpiece)* — Validated multi-gene risk **signature**: continuous
  Cox risk score (NOT median-split) trained on one cohort, **validated on
  independent GEO cohorts** with **Harrell's C-index** + risk-tertile KM. New
  `signature_service.py`, `POST /api/signature`, "Signature" UI tab.
- **F16b** *(M, new)* — **Treatment-effect-modifying (predictive) biomarkers**:
  per-arm HRs + `expression × treatment` interaction p, aggregated across cohorts.
  Genes whose effect is treatment-dependent are flagged predictive in the results.
- **F18** *(M)* — Clinical **nomogram** rendered from Cox coefficients.
- **F19** *(M)* — Established-signature **concordance** benchmark vs public
  Oncotype DX / MammaPrint / PAM50 gene lists (concordance, never coefficient
  reproduction).

**Phase 2 — Clinician UX (hands-on, simple, attractive):**
- **F20** *(M)* — "Oncologist Mode": curated cancer-type **gallery** of pre-run,
  instantly-loaded analyses.
- **F21** *(S/M)* — Plain-language interpretation layer + AI clinician summary
  grounded in the real `AnalysisResponse` (cites genes/HRs/GSEs), framed as
  predictive + advisory.
- **F22** *(M)* — One-page printable clinical **evidence report** with a prominent
  advisory / research-use disclaimer.

**Phase 3 — Investigational (behind advisory disclaimers):**
- **F23** *(L)* — Single-sample risk score + advisory treatment suggestions,
  research-use-only. See §6.
- **F24** *(L)* — Treatment context. See §8.

## 6. Patient-prediction architecture (F23)

**Core reframe — you cannot build a KM curve from one patient.** A KM curve is a
*population* estimator. The correct flow: load patient → compute risk score from a
*locked, pre-validated* signature → assign to a risk group → show *that group's
reference curve* with the patient's predicted position → surface **advisory
treatment suggestions** grounded in documented evidence + treatment-cohort
outcomes. "Predict further behaviour" = predicted t-year survival + risk group,
anchored to a measured C-index. Never a bespoke single-patient curve.

**Separate model-building from patient-scoring:**
1. **Build (F17, offline, once per cancer type)** → locked model artifact: gene
   weights + Cox coefficients + reference expression distribution + reference KM
   per tertile + measured C-index. Version-pinned.
2. **Score (F23, online, instant)** → normalize → dot-product → assign group →
   render → attach advisory treatment suggestions. No per-patient retraining.

**Scoring pipeline:**
1. **Input:** upload a CSV of the tumour's full expression profile → auto-extract
   signature genes. Plus a **built-in demo patient** (real held-out GEO sample).
   CSV processed in-memory only, never persisted.
2. **Normalize against the reference** — rank/quantile-map onto the stored
   reference distribution (single-sample z-score is undefined; rank-against-
   reference is the only defensible cross-platform method).
3. **Compute risk score** = dot-product with locked coefficients.
4. **Assign risk group** by percentile vs reference (tertile).
5. **Render** = reference KM for the assigned group + predicted 1/3/5-year survival
   + C-index + uncertainty note **+ advisory "treatments to consider"** (§8).

`POST /api/predict`: input = model_id + patient expression dict; output = risk
score, group, percentile, t-year survival, reference-group KM.

## 8. Treatment Context & advisory recommendation (F24)

**What it is:** After a patient is scored, the app surfaces **advisory treatment
suggestions** — treatments worth discussing for the patient's profile — combining
(a) documented biomarker→therapy evidence (CIViC/DGIdb) for the risk-driving genes
and (b) survival curves from GEO cohorts where each treatment was documented.
Example: "Documented evidence links *ERBB2* to anti-HER2 therapy (CIViC,
sensitivity, level B). In breast-cancer cohorts receiving adjuvant chemotherapy,
high-risk patients like this one had 42% 5-year survival. Consider discussing with
the tumour board."

**The critical positioning boundary:**
- ✅ Correct framing: *"Treatments to consider/discuss, grounded in documented
  evidence and historical GEO outcomes."*
- ❌ Wrong framing: *"Prescribe X"* or *"this patient will respond to X"* — directive
  / companion-diagnostic claims we must never make.

**Architecture (advisory, evidence-grounded):**
- One model per `(cancer_type, treatment)` pair from treatment-labelled GEO queries
  (e.g., `"breast cancer tamoxifen overall survival"`).
- These estimate outcomes on cohorts that *received* a specific treatment, combined
  with documented biomarker→therapy associations — surfaced as suggestions, not a
  treatment-response model.
- The patient's expression is rank/quantile-normalized onto each treatment cohort's
  reference and assigned to a risk group; the displayed KM is the *reference group
  curve* from that treated cohort.
- Model IDs: `treatment_{cancer_type}_{slug}`, stored in
  `platform_mappings/signature_models/`. Patient expression is never persisted.

**Guardrail language (use verbatim in UI):**
> "Advisory only — treatments to discuss with the care team, grounded in documented
> biomarker evidence and historical outcomes from GEO cohorts. This is not a
> treatment recommendation device, a prescription, or a prediction that this
> patient will respond. Research use only."

**Endpoint:** `POST /api/treatment-context` — input: `{cancer_type, expression,
clinical?}`; output: list of `TreatmentComparison` with KM curves and the patient's
risk group in that treated cohort.

## 7. Guardrails (design constraints, not footnotes)

1. **Advisory / hypothesis-generating language** audited across UI, AI summaries,
   README, reports. Predictive claims are always paired with "validate
   prospectively / research use".
2. **No prescribing language.** Treatment suggestions are framed "to consider /
   discuss"; the `_PRESCRIBING_PATTERN` guardrail strips any directive prose.
3. **Research-use framing** wherever a number could read as a clinical verdict —
   keeps us clear of FDA CDS / EU MDR device territory. UI must never render an
   output as a binding clinical decision.
4. **Interaction tests are underpowered** in small per-arm cohorts and treatment
   annotations are non-standardized — predictive biomarker claims must say so.
5. **Cross-platform normalization** (rank/z within cohort) is mandatory for any
   signature scoring; documented as a method limitation.
6. **No PII** in logs or tool/return values; patient expression accepted in-memory
   only, never persisted.
7. Reuse first: lifelines `CoxPHFitter` + interaction terms + `concordance_index`,
   existing KM/forest components, results-persistence endpoints, the pydantic-ai
   agent, `treatment_context_service` + `therapy_evidence_service`.
