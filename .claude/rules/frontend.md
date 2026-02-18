---
paths:
  - "frontend/**/*"
---

# Frontend Rules

React 18, TypeScript, Redux Toolkit, Tailwind CSS.

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/store/searchSlice.ts` | Redux state |
| `frontend/src/services/api.ts` | API client |
| `frontend/src/components/SearchPage.tsx` | Main page |
| `frontend/src/components/KaplanMeierPlot.tsx` | Survival curves |

## Commands

```bash
npx tsc --noEmit   # Type check
npm run lint        # Lint
npm run build       # Build
```

## Patterns

- Props interfaces defined for all components
- Functional components with hooks only, typed as `React.FC<Props>`
- Redux for shared state, local `useState` for UI-only state
- No `any` types - use proper TypeScript types
- Handle error states in all async operations
