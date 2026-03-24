# Frontend Helper Memory

## Key Interface Locations
- `GeneSurvival`, `GeneDatasetResult`, `HeterogeneityStats` — all in `frontend/src/store/chatSlice.ts`
- Backend response models (source of truth) — `backend/app/models/response_models.py`
- Always check backend Pydantic models when adding new fields to TS interfaces

## Component Patterns
- All components: `React.FC<Props>`, functional with hooks only, no `any` types
- Local tab/toggle state uses `useState`, shared state goes in Redux slices
- Inline type aliases inside component functions are valid TS (`type PlotTab = 'km' | 'forest'`)

## ForestPlot (F08)
- Pure SVG component — not Recharts (Recharts has no forest plot support)
- Located at `frontend/src/components/ForestPlot.tsx`
- Log scale X-axis: `Math.log` maps HR range [0.25, 4.0] to pixel space
- Square marker size = `Math.min(8, Math.max(4, Math.sqrt(n_samples) * 0.4))`
- Pooled estimate rendered as a diamond polygon
- `HeterogeneityStats` fields use `!= null` guard (not `?.`) before calling `.toFixed()` to avoid TS errors on `number | null | undefined`

## KaplanMeierPlot Tab Pattern
- Tab condition: `showForestTab = forestDatasets.length >= 2` (only show tab if enough data)
- Tab state defaults to `'km'` so existing behavior is unchanged for single-dataset genes
- Forest datasets filtered by `Number.isFinite()` on all three HR fields
- Import: `import { ForestPlot } from './ForestPlot'`

## HeterogeneityStats
- Added to `GeneSurvival` as `heterogeneity_stats?: HeterogeneityStats | null`
- Fields: `q_statistic`, `i_squared`, `p_heterogeneity`, `tau_squared` — all `number | null | undefined`
- Backend computes via DerSimonian-Laird in `geo_survival_workflow_orchestrator.py`
