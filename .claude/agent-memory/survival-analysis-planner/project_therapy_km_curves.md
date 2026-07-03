---
name: project-therapy-km-curves
description: Plan for adding Kaplan-Meier cohort curves to the "Treatments to consider" advisory panel (TherapyDirections.tsx) — statistical judgment and implementation design.
metadata:
  type: project
---

Planned (2026-07-04, not yet implemented) — add per-drug KM curves to `frontend/src/components/oncologist/TherapyDirections.tsx`, backed by real GEO cohort data, grounding the currently-unbacked "historical GEO cohort outcomes" clause in `TherapyRationaleResponse.disclaimer` (`backend/app/api/chat_routes.py:508-518`).

**Key finding — three existing KM data sources in the codebase, none directly reusable as-is:**
1. `TreatmentContext`/`SignatureService._reference_km_per_group` (`backend/app/services/signature_service.py:646-675`) — stratifies by a treatment-cohort's *own unrelated multi-gene risk signature* (refit per treatment via the full orchestrator pipeline), not by treated-vs-untreated, and not by the CIViC-flagged gene. No CI. Not defensible as an efficacy curve as-is.
2. `SurvivalAnalysisService._detect_treatment_column`/`_binarize_treatment`/`_fit_interaction_cox` (`backend/app/services/survival_analysis_service.py:786-959`) — true treated-vs-untreated (or top-2-category) arms within one GSE, but only fits Cox HR today, no KM. Confounding-by-indication risk (observational, not randomized). Arm label is NOT guaranteed drug-specific — confirmed via `backend/data/therapy_evidence.json` that DGIdb drug strings are messy (salts, combos, casing), so a text-match guard between drug name and raw arm category is required before attributing a curve to a specific drug.
3. `_analyze_gene_survival` (`survival_analysis_service.py:997-1193`) — median-expression-split KM with CI bands (`KMCurveData`, `response_models.py:9-16`). Answers a different question (prognostic, not treatment) but is the implementation quality bar (CI fitting/sanitization pattern) to reuse.

**Recommendation:** three-tier fallback, never fabricate — (1) within-cohort treated/untreated KM (source 2, extended with KM+CI, gated by drug-name match + min 5 samples/10 events per arm, labeled "not a randomized comparison"), (2) relabeled matched-cohort reference (source 1, visually de-emphasized, labeled "not compared to an untreated arm"), (3) explicit "no cohort data available" text. Full plan with backend field/endpoint changes and frontend integration written to `/home/svarog/.claude/plans/use-claude-agents-survival-analysis-plan-humming-book-agent-a8df4416743d21169.md`.

**Why:** the project's differentiation mandate (`.claude/rules/chat_agent.md`) forbids hallucinating a capability; reusing either existing KM source unmodified would overclaim a causal treated-vs-control effect the data doesn't support.

**How to apply:** if asked to implement this feature, start from the plan file above rather than re-deriving the analysis. If the plan file has been deleted/superseded, the tiering logic and the three source citations here are the load-bearing facts to preserve.
