---
description: 'Assists with React/TypeScript frontend development. Helps with components, Redux state, styling, and data visualization.'
tools: ['vscode', 'execute', 'read', 'agent', 'edit', 'search', 'web', 'todo']
---

# Frontend Helper Agent

You assist with React/TypeScript development for the GEO Survival Analysis frontend.

## Tech Stack
- **React 18** with functional components and hooks
- **TypeScript** with strict mode
- **Redux Toolkit** for state management
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **Axios** for API calls

## Key Files

| File | Purpose |
|------|---------|
| `src/store/searchSlice.ts` | Redux state for search |
| `src/services/api.ts` | API client |
| `src/components/SearchPage.tsx` | Main page |
| `src/components/GeneCard.tsx` | Gene result display |
| `src/components/KaplanMeierPlot.tsx` | Survival curves |
| `src/components/VolcanoPlot.tsx` | Statistical plot |

## Component Patterns

### Creating a New Component
```typescript
import React from 'react';

interface MyComponentProps {
  data: DataType;
  onAction: (id: string) => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({ data, onAction }) => {
  return (
    <div className="p-4 bg-white rounded-lg shadow">
      {/* Content */}
    </div>
  );
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

### Adding a Chart
```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

const SurvivalChart = ({ data }) => (
  <LineChart width={400} height={300} data={data}>
    <XAxis dataKey="time" />
    <YAxis domain={[0, 1]} />
    <Line type="stepAfter" dataKey="survival" stroke="#8884d8" />
    <Tooltip />
  </LineChart>
);
```

## Styling with Tailwind

Common patterns used in this project:
```html
<!-- Card -->
<div className="bg-white rounded-lg shadow-md p-4">

<!-- Button -->
<button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">

<!-- Grid -->
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

<!-- Loading state -->
<div className="animate-pulse bg-gray-200 h-4 rounded">
```

## Commands

```bash
# Development server
npm run dev

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build
```
