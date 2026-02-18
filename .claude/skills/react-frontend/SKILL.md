---
name: react-frontend
description: React/TypeScript frontend development patterns. Use when creating components, managing Redux state, building Recharts visualizations, or styling with Tailwind CSS.
---

# React Frontend Patterns

## Tech Stack

React 18, TypeScript strict, Redux Toolkit, Tailwind CSS, Recharts, Axios, Vite

## Project Structure

```
frontend/src/
├── components/           # React components
│   ├── SearchPage.tsx    # Main page
│   ├── SearchBar.tsx     # Search input
│   ├── GeneCard.tsx      # Gene result card
│   ├── KaplanMeierPlot.tsx
│   └── VolcanoPlot.tsx
├── store/
│   ├── store.ts          # Redux store config
│   └── searchSlice.ts    # Search state
└── services/
    └── api.ts            # Axios client
```

## Component Pattern

```typescript
interface GeneCardProps {
  gene: GeneSurvivalResponse;
  isExpanded: boolean;
  onToggle: () => void;
}

export const GeneCard: React.FC<GeneCardProps> = ({ gene, isExpanded, onToggle }) => (
  <div className="bg-white rounded-lg shadow-md p-4 cursor-pointer hover:shadow-lg transition-shadow"
       onClick={onToggle}>
    <div className="flex justify-between items-center">
      <h3 className="text-lg font-semibold">{gene.gene_symbol}</h3>
      <span className={`px-2 py-1 rounded text-sm ${
        gene.hazard_ratio > 1 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
      }`}>HR: {gene.hazard_ratio.toFixed(2)}</span>
    </div>
    {isExpanded && (
      <div className="mt-4 border-t pt-4">
        <p>P-value: {gene.p_value.toExponential(2)}</p>
      </div>
    )}
  </div>
);
```

## Redux Slice

```typescript
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

interface SearchState {
  query: string;
  results: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
}

export const searchGenes = createAsyncThunk(
  'search/searchGenes',
  async (params: SearchParams, { rejectWithValue }) => {
    try {
      return (await searchAPI(params)).data;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Search failed');
    }
  }
);

export const searchSlice = createSlice({
  name: 'search',
  initialState: { query: '', results: null, loading: false, error: null },
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => { state.query = action.payload; },
    clearResults: (state) => { state.results = null; state.error = null; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(searchGenes.pending, (state) => { state.loading = true; state.error = null; })
      .addCase(searchGenes.fulfilled, (state, action) => { state.loading = false; state.results = action.payload; })
      .addCase(searchGenes.rejected, (state, action) => { state.loading = false; state.error = action.payload as string; });
  },
});
```

## Recharts: Kaplan-Meier Curve

```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts';

export const KaplanMeierPlot: React.FC<{ data: KMData[] }> = ({ data }) => (
  <LineChart width={500} height={300} data={data}>
    <XAxis dataKey="time" label={{ value: 'Time (months)', position: 'bottom' }} />
    <YAxis domain={[0, 1]} label={{ value: 'Survival Probability', angle: -90, position: 'left' }} />
    <Tooltip /><Legend />
    <Line type="stepAfter" dataKey="survival_high" stroke="#ef4444" name="High Expression" dot={false} />
    <Line type="stepAfter" dataKey="survival_low" stroke="#22c55e" name="Low Expression" dot={false} />
  </LineChart>
);
```

## Tailwind Patterns

```html
<!-- Card -->       <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
<!-- Button -->     <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50">
<!-- Grid -->       <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
<!-- Loading -->    <div className="animate-pulse bg-gray-200 h-4 rounded">
<!-- Risk badge --> <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
```

## TypeScript Types

```typescript
interface AnalysisResponse {
  query: string;
  datasets_analyzed: number;
  genes: GeneSurvivalResponse[];
}

interface GeneSurvivalResponse {
  gene_symbol: string;
  hazard_ratio: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  datasets: GeneDatasetResult[];
}

type RootState = ReturnType<typeof store.getState>;
type AppDispatch = typeof store.dispatch;
```

## Commands

```bash
cd frontend && npm run dev       # Dev server
cd frontend && npx tsc --noEmit  # Type check
cd frontend && npm run lint      # Lint
cd frontend && npm run build     # Build
```
