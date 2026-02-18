# Redux Toolkit Exercises

Exercises based on patterns from `frontend/src/store/searchSlice.ts`, `authSlice.ts`, and `chatSlice.ts`.

## Beginner

### Exercise 1: Create a Simple Slice
**Task**: Create a `filterSlice` for managing gene result filters: `significanceThreshold` (number), `minHazardRatio` (number), `showOnlySignificant` (boolean), `sortBy` (string). Include reducers to update each field and a `resetFilters` action.
**Starter code**:
```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface FilterState {
  significanceThreshold: number;
  minHazardRatio: number;
  showOnlySignificant: boolean;
  sortBy: 'hazard_ratio' | 'p_value' | 'gene_symbol';
}

// TODO: Define initialState
// TODO: Create filterSlice with createSlice
// TODO: Add reducers: setThreshold, setMinHR, toggleSignificant, setSortBy, resetFilters
// TODO: Export actions and reducer
```
**Test criteria**:
- Each reducer correctly updates its field via Immer
- resetFilters restores initialState, toggleSignificant flips boolean
**Key concepts**: createSlice, PayloadAction, Immer mutations, initialState

### Exercise 2: Use useSelector and useDispatch
**Task**: Create a `FilterControls` component that reads filter state from Redux store using `useSelector` and dispatches actions using `useDispatch`. Include a threshold slider, checkbox, and sort dropdown.
**Starter code**:
```typescript
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../store/store';

// TODO: Create FilterControls component that:
//   1. useSelector to read filter state from store
//   2. useDispatch to get dispatch function
//   3. Render threshold slider dispatching setThreshold
//   4. Render checkbox dispatching toggleSignificant
//   5. Render sort dropdown dispatching setSortBy
//   6. Reset button dispatching resetFilters
```
**Test criteria**:
- Component reads correct slice from store, dispatches on user interaction
- UI reflects current store state
**Key concepts**: useSelector, useDispatch, RootState type, action dispatch

## Intermediate

### Exercise 3: createAsyncThunk with Loading States
**Task**: Create an async thunk `fetchGeneDetails` that calls an API endpoint, and wire it into a slice with pending/fulfilled/rejected states. Handle error messages with `rejectWithValue`.
**Starter code**:
```typescript
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

interface GeneDetails { gene_symbol: string; description: string; pathways: string[]; }
interface GeneDetailState { data: GeneDetails | null; loading: boolean; error: string | null; }

// TODO: Create fetchGeneDetails thunk that:
//   1. Accepts geneId: string as argument
//   2. Calls api.get(`/api/genes/${geneId}`)
//   3. Returns response.data on success
//   4. Calls rejectWithValue(message) on error

// TODO: Create geneDetailSlice with:
//   1. initialState with null data, false loading, null error
//   2. reducers: clearGeneDetails
//   3. extraReducers handling pending/fulfilled/rejected
```
**Test criteria**:
- pending sets loading=true and error=null
- fulfilled sets data and loading=false
- rejected sets error message and loading=false
**Key concepts**: createAsyncThunk, extraReducers, rejectWithValue, lifecycle actions

### Exercise 4: Memoized Selectors
**Task**: Create memoized selectors that derive computed state: `selectSignificantGenes` (filtered by p-value), `selectGenesByRisk` (grouped into high/low risk), `selectSummaryStats` (count, mean HR, min p-value).
**Starter code**:
```typescript
import { createSelector } from '@reduxjs/toolkit';
import { RootState } from './store';

// TODO: selectSearchResults - base selector for results
// TODO: selectSignificantGenes - filter by p_value < threshold from filter slice
// TODO: selectGenesByRisk - returns { highRisk: Gene[], lowRisk: Gene[] }
// TODO: selectSummaryStats - returns { total, significant, meanHR, minPValue }
```
**Test criteria**:
- Selectors memoize correctly (same input → same reference)
- selectGenesByRisk splits by hazard_ratio > 1 vs <= 1
- selectSummaryStats computes correct aggregations
**Key concepts**: createSelector, memoization, derived state, input selectors

## Advanced

### Exercise 5: Optimistic Updates
**Task**: Implement optimistic update for a "favorite gene" feature. When user clicks favorite, immediately update UI, send API request, and revert on failure. Use `dispatch` within the thunk to update state before the API call.
**Starter code**:
```typescript
// TODO: Add favoritedGenes: string[] to search state
// TODO: Create toggleFavorite thunk that:
//   1. Reads current favorites from getState()
//   2. Dispatches optimistic update (add/remove from array)
//   3. Calls API to persist the change
//   4. On failure: dispatches revert action and shows error
// TODO: Add reducers: addFavorite, removeFavorite (for optimistic updates)
```
**Test criteria**:
- UI updates immediately before API response
- On API failure, state reverts to previous value
- Toggle adds if not present, removes if present
**Key concepts**: Optimistic updates, getState(), dispatch within thunk, rollback

### Exercise 6: Normalized State with Entity Adapter
**Task**: Use `createEntityAdapter` to manage a collection of datasets with normalized state. Include selectors for `selectAll`, `selectById`, sorted by date. Add async thunks for CRUD operations.
**Starter code**:
```typescript
import { createEntityAdapter, createSlice, createAsyncThunk } from '@reduxjs/toolkit';

interface Dataset { id: string; title: string; organism: string; createdAt: string; }

// TODO: Create datasetsAdapter with sortComparer by createdAt
// TODO: Create slice using adapter.getInitialState({ loading, error })
// TODO: Create thunks: fetchDatasets, addDataset, removeDataset
// TODO: Use adapter methods: setAll, addOne, removeOne in extraReducers
// TODO: Export adapter selectors: selectAll, selectById, selectTotal
```
**Test criteria**:
- Entities stored in normalized `{ ids: [], entities: {} }` format
- Selectors return denormalized data, sorted by createdAt descending
- CRUD operations update normalized state correctly
**Key concepts**: createEntityAdapter, normalized state, entity selectors, CRUD
