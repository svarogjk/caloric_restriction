---
paths:
  - "frontend/**/*"
---

# Frontend Rules

React 18, TypeScript, Redux Toolkit, Tailwind CSS.

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/store/chatSlice.ts` | Chat + analysis Redux state |
| `frontend/src/store/authSlice.ts` | Auth Redux state |
| `frontend/src/services/api.ts` | Analysis API client |
| `frontend/src/components/KaplanMeierPlot.tsx` | Survival curves |
| `frontend/src/components/ForestPlot.tsx` | Forest plot visualization |

## Patterns

- Props interfaces defined for all components
- Functional components with hooks only, typed as `React.FC<Props>`
- Redux for shared state, local `useState` for UI-only state
- No `any` types - use proper TypeScript types
- Handle error states in all async operations
