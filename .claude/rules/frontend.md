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
# Start dev server
cd frontend && npm run dev

# Type check
cd frontend && npx tsc --noEmit

# Lint
cd frontend && npm run lint

# Build
cd frontend && npm run build
```

## Code Patterns

### Adding a Component
```typescript
interface Props {
  data: DataType;
  onAction: () => void;
}

export const NewComponent: React.FC<Props> = ({ data, onAction }) => {
  return <div>...</div>;
};
```

### Using Redux
```typescript
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../store/store';
import { setQuery, searchGenes } from '../store/searchSlice';

const MyComponent = () => {
  const dispatch = useDispatch();
  const { query, results, loading } = useSelector((state: RootState) => state.search);

  const handleSearch = () => {
    dispatch(searchGenes(query));
  };
};
```

### Tailwind Patterns
```html
<!-- Card -->
<div className="bg-white rounded-lg shadow-md p-4">

<!-- Button -->
<button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">

<!-- Grid -->
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

## Requirements

- Props interfaces defined for all components
- Functional components with hooks only
- Redux for shared state, local state for UI-only
- No `any` types - use proper TypeScript types
- Error states handled in async operations
