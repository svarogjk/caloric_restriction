---
description: Show product roadmap with feature status. Update checkboxes as features are implemented and verified.
user-invocable: true
---

# Product Roadmap

Check off features as they are implemented and verified. Use `/implement-feature F01` to start any feature.

## Phase 1 — Immediate Wins (S/M)

- [x] **F01** Remove mock KM data [S] — `KaplanMeierPlot.tsx`
- [x] **F02** Gene search + filter + pagination [S] — `AnalysisResultsDisplay.tsx`
- [x] **F03** CI bands on KM curves [S] — `KaplanMeierPlot.tsx`
- [x] **F04** CSV + PNG export [S] — `AnalysisResultsDisplay.tsx` + `KaplanMeierPlot.tsx`
- [x] **F05** Analysis progress SSE [M] — `routes.py` + `orchestrator.py` + `ChatContainer.tsx`
- [x] **F06** Enable chat streaming [M] — `chatApi.ts` + `chatSlice.ts` + `MessageList.tsx`
- [x] **F07** Persist analysis results to database [M] — `database.py` + `routes.py` + `chatSlice.ts`

## Phase 2 — Core Differentiators (M)

- [x] **F08** Forest plot tab [M] — `AnalysisResultsDisplay.tsx` + new `ForestPlot.tsx`
- [x] **F09** Shareable result URLs [M] — `routes.py` + `App.tsx` *(requires F07)*
- [x] **F10** Gene batch input mode [M] — `request_models.py` + `orchestrator.py`
- [ ] **F11** Pathway/GO enrichment [M] — new `enrichment_service.py`

## Phase 3 — Power User Features (L)

- [x] **F12** Analysis history dashboard [M] — `routes.py` + new `AnalysisHistoryPage.tsx` *(requires F07)*
- [x] **F13** Multivariate Cox regression [L] — `survival_analysis_service.py` *(surfaced by F16)*
- [x] **F14** Analysis comparison mode [L] — new `comparison_service.py` *(requires F07, F12)*
- [x] **F15** Publication export package [L] — new `export_service.py` *(requires F07)*

## Phase 4 — Clinical Decision Support (prognostic, RUO)

See the `clinical-positioning` skill for positioning. All prognostic, research-use-only.

- [x] **F16** Surface multivariate (adjusted) Cox HRs in UI [M] — `routes.py` + `AnalysisResultsDisplay.tsx`
- [x] **F17** Validated multi-gene prognostic signature [L] — new `signature_service.py` + `POST /api/signature` + `SignaturePanel.tsx`
- [x] **F18** Clinical nomogram (SVG) [M] — new `NomogramSVG.tsx` *(consumes F17 model)*
- [x] **F19** Established-signature concordance benchmark [M] — new `ConcordanceBenchmark.tsx` + `establishedSignatures.ts`
- [x] **F20** Oncologist Mode gallery [M] — new `gallery_routes.py` + `OncologistGallery.tsx`
- [x] **F21** Plain-language interpretation + AI clinician summary [S/M] — `POST /api/chat/interpret` + `ClinicianSummary.tsx` + `InfoTooltip.tsx`
- [x] **F22** One-page printable clinical evidence report [M] — new `ClinicalReport.tsx` + `@media print` in `index.css`
- [x] **F23** Single-sample risk score (RUO) [L] — `signature_service.py` + `POST /api/predict` *(consumes F17 model)*

## Competitive Positioning

| Competitor | Their Strength | Our Counter |
|---|---|---|
| KMPlot | PNG export, fast curated db | F03+F04 match quality; F08 Forest Plot is unique |
| GEPIA2 | TCGA + pathway analysis | F11 enrichment matches; GEO breadth >> TCGA |
| cBioPortal | Multi-omics, established | F10 batch + NL interface lowers barrier |
| OncoLnc | Simple, fast (TCGA only) | Multi-dataset consistency = uncopyable moat |

## Usage

- `/roadmap` — view this checklist
- `/implement-feature F01` — start implementing a specific feature
- `/strategize` — research market and propose new features
- `/cleanup F04` — review and improve an implemented feature
