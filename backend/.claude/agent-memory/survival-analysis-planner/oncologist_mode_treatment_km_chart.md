---
name: oncologist-mode-treatment-km-chart
description: Design decisions for the Oncologist Mode "top N treatments" combined KM chart (selection, on-demand fetch caps, evidentiary gate, cross-cohort overlay)
metadata:
  type: project
---

Strategy agreed 2026-07-18 for `TherapyDirections.tsx` / `signatureViz.ts` /
`chat_routes.py::therapy_rationale` (F24b combined "top N treatments" KM chart).

**Root cause of "almost no curves render"**: `uniqueEvidenceDrugs()` in
`signatureViz.ts` orders drugs by first-appearance in the CIViC/DGIdb evidence
table, which is dominated by whichever gene has the most rows. The backend
only resolves `cohort_km` for a *different* 8-drug set chosen by
`_select_top_drugs` (round-robin across genes, CIViC level A/B tiebreak) in
`chat_routes.py`. Zero overlap between the two rankings ⇒ most frontend
"top N" picks are stuck at `tier="not_checked"` forever, since the frontend
never calls `/therapy-rationale/cohort-km` for drugs outside its own
mis-ranked list.

**Decision 1 — ranking**: the backend's `_select_top_drugs` (round-robin
across risk-driving genes, CIViC-level ordering within a gene) is the
scientifically correct criterion and should be the single source of truth.
Expose it explicitly (e.g. add `ranked_drugs: list[str]` to
`TherapyRationaleResponse`) instead of re-deriving a ranking in TypeScript —
avoids the two rankings drifting apart again.

**Decision 2 — exclude resistance-flavored evidence from the "to plot"
selection.** CIViC `significance` (in `therapy_evidence_service.py`, values
like "Resistance"/"Adverse Response") is not filtered anywhere before
`_select_top_drugs`. A resistance marker plotted as a curve next to the
patient's baseline visually implies "consider this," which contradicts the
evidence and the app's advisory-only positioning. Filter significance
containing resistance/adverse/poor-outcome out of the *plot* selection (the
underlying evidence table can still show it, cited, since disclosure there is
honest — the risk is specifically in promoting it to a comparison curve).

**Decision 3 — minimum evidentiary bar to plot a curve**: gate on the
curve's own `n_events`/`n_samples`, not just the whole-cohort build gate.
Tier 1 (`TreatmentArmKM`) already enforces `n_events >= 10` per arm at fit
time (`_fit_treatment_arm_km` in `survival_analysis_service.py`) — solid.
Tier 2 (`ReferenceKMCurve`, from `PrognosticModel.reference_km`) only
enforces a whole-cohort floor (`MIN_TRAIN_SAMPLES=20`, `MIN_EVENTS=5` in
`signature_service.py`) *before* splitting into 3 risk-tertile groups — an
individual tertile curve can end up far below that. Add an explicit
per-curve gate before plotting Tier 2: recommend `n_events >= 5` (matches
existing `MIN_EVENTS` convention) and `n_samples >= 15`.

**Decision 4 — don't merge tiers as directly-comparable lines.** Tier 1
(arm_comparison) is same-cohort/observational; Tier 2 (cohort_reference) is
a different cohort/population entirely; baseline is the patient's own
training-cohort curve. Distinguish visually per tier (line style — solid
Tier 1 / dotted Tier 2 / thick-dashed baseline, already supported by
`KMChartCurve.dashed`/`strokeWidth` in `KaplanMeierChart.tsx`) and surface
each curve's `caveat` field (`ARM_COMPARISON_CAVEAT` /
`COHORT_REFERENCE_CAVEAT`, already computed server-side but currently
dropped by `topTreatmentCurves()`) inline, not just generic panel
boilerplate. When both tiers exist for the same drug, prefer Tier 1 (more
internally valid, same cohort) and only fall back to Tier 2.

**Decision 5 — on-demand fetch cap.** `TreatmentContextService._building`
(`treatment_context_service.py`) only dedupes rebuilding the *same*
model_id — there is no global concurrency cap on how many distinct Tier-2
builds can run at once, and each uncached, non-curated-name build is a real
~2-5 min GEO download+orchestrator run. Curated `TREATMENT_QUERIES` entries
(~3 per cancer type) are cheap once warmed via `/warm`; arbitrary CIViC/DGIdb
drug names usually are not curated and will trigger a fresh build. Cap
frontend-triggered on-demand batches to the existing `_MAX_COHORT_KM_DRUGS`
(8) per call, and gate anything beyond the initial auto-resolved 8 behind an
explicit user action (e.g. a "check more" button), not an automatic effect
that fires on every `topN` slider change.

**Verified NOT a bug**: `_fit_treatment_arm_km` always appends arms in fixed
order `(0, 1)` i.e. `[untreated/control, treated]`, so the frontend's
`arms[arms.length - 1]` in `topTreatmentCurves()` correctly picks the
treated arm.

**Structural limitation (not fixable by a frontend change)**: `KMCurveData`
(used by Tier 1 `TreatmentArmKM.km_curve`) has `ci_lower`/`ci_upper`, but
`ReferenceKMCurve` (used by Tier 2 `reference_km` and by the patient
baseline) has no CI fields at all — Tier 2 structurally cannot show
uncertainty bands without a backend model change. `topTreatmentCurves()`
currently drops CI even for Tier 1 where it *is* available — that part is a
quick, real fix.

Related: [[therapy_evidence_significance_filter]] if that gets split out
later; see also `[[user_communication_style]]`.
