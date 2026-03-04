---
description: Show product roadmap with feature status. Update checkboxes as features are implemented and verified.
user-invocable: true
---

# Product Roadmap

Check off features as they are implemented and verified. Use `/implement-feature F01` to start any feature.

## Phase 1 — Immediate Wins (S/M)

- [ ] **F01** Remove mock KM data [S] — `KaplanMeierPlot.tsx`
- [ ] **F02** Gene search + filter + pagination [S] — `AnalysisResultsDisplay.tsx`
- [ ] **F03** CI bands on KM curves [S] — `KaplanMeierPlot.tsx`
- [ ] **F04** CSV + PNG export [S] — `AnalysisResultsDisplay.tsx` + `KaplanMeierPlot.tsx`
- [ ] **F05** Analysis progress SSE [M] — `routes.py` + `orchestrator.py` + `ChatContainer.tsx`
- [ ] **F06** Enable chat streaming [M] — `chatApi.ts` + `chatSlice.ts` + `MessageList.tsx`
- [ ] **F07** Persist analysis results to database [M] — `database.py` + `routes.py` + `chatSlice.ts`

## Phase 2 — Core Differentiators (M)

- [ ] **F08** Forest plot tab [M] — `AnalysisResultsDisplay.tsx` + new `ForestPlot.tsx`
- [ ] **F09** Shareable result URLs [M] — `routes.py` + `App.tsx` *(requires F07)*
- [ ] **F10** Gene batch input mode [M] — `request_models.py` + `orchestrator.py`
- [ ] **F11** Pathway/GO enrichment [M] — new `enrichment_service.py`

## Phase 3 — Power User Features (L)

- [ ] **F12** Analysis history dashboard [M] — `routes.py` + new `AnalysisHistoryPage.tsx` *(requires F07)*
- [ ] **F13** Multivariate Cox regression [L] — `survival_analysis_service.py`
- [ ] **F14** Analysis comparison mode [L] — new `comparison_service.py` *(requires F07, F12)*
- [ ] **F15** Publication export package [L] — new `export_service.py` *(requires F07)*

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
