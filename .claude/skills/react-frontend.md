# React Frontend Skill

Use this skill when working on React components, Redux state management, Tailwind styling, or Recharts visualizations in the frontend.

## Tech Stack

- **React 18** with functional components
- **TypeScript** strict mode
- **Redux Toolkit** for state management
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **Axios** for API calls
- **Vite** for build tooling

## Project Structure

```
frontend/src/
├── components/           # React components
│   ├── SearchPage.tsx    # Main page
│   ├── SearchBar.tsx     # Search input
│   ├── GeneCard.tsx      # Gene result card
│   ├── GeneList.tsx      # Results list
│   ├── KaplanMeierPlot.tsx
│   └── VolcanoPlot.tsx
├── store/
│   ├── store.ts          # Redux store config
│   └── searchSlice.ts    # Search state
└── services/
    └── api.ts            # Axios client
```

## Component Patterns

### Basic Component
```typescript
import React from 'react';

interface GeneCardProps {
  gene: GeneSurvivalResponse;
  isExpanded: boolean;
  onToggle: () => void;
}

export const GeneCard: React.FC<GeneCardProps> = ({
  gene,
  isExpanded,
  onToggle
}) => {
  return (
    <div
      className="bg-white rounded-lg shadow-md p-4 cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onToggle}
    >
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">{gene.gene_symbol}</h3>
        <span className={`px-2 py-1 rounded text-sm ${
          gene.hazard_ratio > 1
            ? 'bg-red-100 text-red-800'
            : 'bg-green-100 text-green-800'
        }`}>
          HR: {gene.hazard_ratio.toFixed(2)}
        </span>
      </div>

      {isExpanded && (
        <div className="mt-4 border-t pt-4">
          <p>P-value: {gene.p_value.toExponential(2)}</p>
          <p>CI: [{gene.ci_lower.toFixed(2)}, {gene.ci_upper.toFixed(2)}]</p>
        </div>
      )}
    </div>
  );
};
```

### Component with Hooks
```typescript
import React, { useState, useEffect, useMemo, useCallback } from 'react';

export const GeneList: React.FC<{ genes: Gene[] }> = ({ genes }) => {
  const [sortBy, setSortBy] = useState<'pvalue' | 'hr'>('pvalue');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Memoize expensive computation
  const sortedGenes = useMemo(() => {
    return [...genes].sort((a, b) => {
      if (sortBy === 'pvalue') return a.p_value - b.p_value;
      return Math.abs(Math.log(b.hazard_ratio)) - Math.abs(Math.log(a.hazard_ratio));
    });
  }, [genes, sortBy]);

  // Memoize callback
  const handleToggle = useCallback((id: string) => {
    setExpandedId(prev => prev === id ? null : id);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => setSortBy('pvalue')}
          className={sortBy === 'pvalue' ? 'btn-active' : 'btn'}
        >
          Sort by P-value
        </button>
        <button
          onClick={() => setSortBy('hr')}
          className={sortBy === 'hr' ? 'btn-active' : 'btn'}
        >
          Sort by Hazard Ratio
        </button>
      </div>

      {sortedGenes.map(gene => (
        <GeneCard
          key={gene.gene_symbol}
          gene={gene}
          isExpanded={expandedId === gene.gene_symbol}
          onToggle={() => handleToggle(gene.gene_symbol)}
        />
      ))}
    </div>
  );
};
```

## Redux Patterns

### Slice Definition
```typescript
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { searchAPI } from '../services/api';

interface SearchState {
  query: string;
  results: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
}

const initialState: SearchState = {
  query: '',
  results: null,
  loading: false,
  error: null,
};

export const searchGenes = createAsyncThunk(
  'search/searchGenes',
  async (params: SearchParams, { rejectWithValue }) => {
    try {
      const response = await searchAPI(params);
      return response.data;
    } catch (error) {
      if (error instanceof Error) {
        return rejectWithValue(error.message);
      }
      return rejectWithValue('Search failed');
    }
  }
);

export const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload;
    },
    clearResults: (state) => {
      state.results = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(searchGenes.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(searchGenes.fulfilled, (state, action) => {
        state.loading = false;
        state.results = action.payload;
      })
      .addCase(searchGenes.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { setQuery, clearResults } = searchSlice.actions;
```

### Using Redux in Components
```typescript
import { useSelector, useDispatch } from 'react-redux';
import type { RootState, AppDispatch } from '../store/store';
import { setQuery, searchGenes } from '../store/searchSlice';

export const SearchBar: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { query, loading } = useSelector((state: RootState) => state.search);

  const handleSearch = () => {
    dispatch(searchGenes({ query, max_datasets: 10 }));
  };

  return (
    <div className="flex gap-2">
      <input
        type="text"
        value={query}
        onChange={(e) => dispatch(setQuery(e.target.value))}
        className="flex-1 px-4 py-2 border rounded-lg"
        placeholder="Search genes..."
      />
      <button
        onClick={handleSearch}
        disabled={loading}
        className="px-6 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
      >
        {loading ? 'Searching...' : 'Search'}
      </button>
    </div>
  );
};
```

## Recharts Visualization

### Kaplan-Meier Curve
```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from 'recharts';

interface KMData {
  time: number;
  survival_high: number;
  survival_low: number;
}

export const KaplanMeierPlot: React.FC<{ data: KMData[] }> = ({ data }) => {
  return (
    <LineChart width={500} height={300} data={data}>
      <XAxis
        dataKey="time"
        label={{ value: 'Time (months)', position: 'bottom' }}
      />
      <YAxis
        domain={[0, 1]}
        label={{ value: 'Survival Probability', angle: -90, position: 'left' }}
      />
      <Tooltip />
      <Legend />
      <Line
        type="stepAfter"
        dataKey="survival_high"
        stroke="#ef4444"
        name="High Expression"
        dot={false}
      />
      <Line
        type="stepAfter"
        dataKey="survival_low"
        stroke="#22c55e"
        name="Low Expression"
        dot={false}
      />
    </LineChart>
  );
};
```

### Volcano Plot
```typescript
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, Cell } from 'recharts';

interface VolcanoPoint {
  gene: string;
  logHR: number;
  negLogP: number;
}

export const VolcanoPlot: React.FC<{ data: VolcanoPoint[] }> = ({ data }) => {
  return (
    <ScatterChart width={600} height={400}>
      <XAxis
        dataKey="logHR"
        domain={[-3, 3]}
        label={{ value: 'log2(Hazard Ratio)', position: 'bottom' }}
      />
      <YAxis
        dataKey="negLogP"
        label={{ value: '-log10(p-value)', angle: -90, position: 'left' }}
      />
      <Tooltip content={({ payload }) => (
        payload?.[0] && (
          <div className="bg-white p-2 shadow rounded">
            <p className="font-bold">{payload[0].payload.gene}</p>
            <p>HR: {Math.exp(payload[0].payload.logHR).toFixed(2)}</p>
          </div>
        )
      )} />
      <Scatter data={data}>
        {data.map((entry, index) => (
          <Cell
            key={index}
            fill={entry.logHR > 0 ? '#ef4444' : '#22c55e'}
          />
        ))}
      </Scatter>
    </ScatterChart>
  );
};
```

## Tailwind Patterns

```html
<!-- Card -->
<div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">

<!-- Button variants -->
<button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50">
<button className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50">

<!-- Loading skeleton -->
<div className="animate-pulse space-y-2">
  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
</div>

<!-- Grid layout -->
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

<!-- Flex layout -->
<div className="flex items-center justify-between gap-4">

<!-- Status badges -->
<span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
<span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
```

## TypeScript Types

```typescript
// API Response types
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

interface GeneDatasetResult {
  dataset_id: string;
  hazard_ratio: number;
  p_value: number;
  km_data: KMDataPoint[];
}

// Redux types
type RootState = ReturnType<typeof store.getState>;
type AppDispatch = typeof store.dispatch;
```
