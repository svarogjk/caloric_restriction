# React/TypeScript Exercises

Exercises based on patterns from `frontend/src/components/` and the project's React 18 + TypeScript strict setup.

## Beginner

### Exercise 1: Typed Functional Component
**Task**: Create a `DatasetCard` component that displays a GEO dataset's accession, title, organism, and sample count. Use a typed interface for props. Apply Tailwind classes for card styling with hover effect. Show a colored badge for organism type.
**Starter code**:
```typescript
// TODO: Define DatasetCardProps interface with:
//   accession: string, title: string, organism: string, sampleCount: number

// TODO: Create DatasetCard: React.FC<DatasetCardProps> that renders:
//   - Card container with bg-white rounded-lg shadow-md p-4 hover:shadow-lg
//   - Accession as header (text-lg font-semibold)
//   - Title as paragraph
//   - Organism badge with conditional color (human=blue, mouse=green, other=gray)
//   - Sample count display
```
**Test criteria**:
- Renders all props correctly, organism badge has correct color class
- Component accepts and destructures typed props
**Key concepts**: React.FC, TypeScript interface, props destructuring, conditional className

### Exercise 2: Conditional Rendering with Loading/Error States
**Task**: Create a `ResultsPanel` that shows a loading spinner when `loading=true`, an error message when `error` is set, an empty state when `results` is null, and the actual results list otherwise.
**Starter code**:
```typescript
interface ResultsPanelProps {
  loading: boolean;
  error: string | null;
  results: { gene_symbol: string; p_value: number }[] | null;
}

// TODO: Create ResultsPanel with 4 render states:
//   1. loading → spinner with "Analyzing..." text
//   2. error → red alert box with error message
//   3. null results → "No results yet" placeholder
//   4. results → mapped list of gene cards
```
**Test criteria**:
- Shows correct state for each combination of props
- Error state shows the error message text, loading shows spinner
**Key concepts**: Conditional rendering, union types, null checks, loading states

## Intermediate

### Exercise 3: API Data Fetching with useEffect
**Task**: Create a `ModelSelector` component that fetches available models from `/api/models` on mount, displays them in a dropdown, handles loading/error states, and calls `onSelect` when user picks a model. Use proper cleanup for the fetch.
**Starter code**:
```typescript
interface ModelSelectorProps {
  selectedModel: string;
  onSelect: (model: string) => void;
}

// TODO: Create ModelSelector that:
//   1. useState for models list, loading, error
//   2. useEffect to fetch /api/models on mount
//   3. Cleanup flag to prevent state update after unmount
//   4. Render loading/error/select states
//   5. Call onSelect when dropdown changes
```
**Test criteria**:
- Fetches on mount, cleanup prevents state updates after unmount
- Loading state shown during fetch, error state on failure
**Key concepts**: useEffect, useState, fetch cleanup, controlled select

### Exercise 4: Form with Validation
**Task**: Create a `SearchForm` component with: query text input (required, max 500 chars), dataset count slider (1-50), organism dropdown (optional), and a submit button. Validate on submit, show inline error messages, disable submit while invalid or loading.
**Starter code**:
```typescript
interface SearchFormProps {
  onSubmit: (params: SearchParams) => void;
  loading: boolean;
}

// TODO: Define SearchParams interface
// TODO: Create SearchForm with:
//   1. useState for each form field and errors object
//   2. Validation function checking all constraints
//   3. handleSubmit that validates then calls onSubmit
//   4. Inline error messages below invalid fields
//   5. Submit button disabled when loading or invalid
```
**Test criteria**:
- Validates required query, max length, numeric ranges
- Shows/hides inline errors, button disabled appropriately
**Key concepts**: Form state, validation, controlled inputs, error display

## Advanced

### Exercise 5: useMemo for Data Transformation
**Task**: Create a `GeneTable` that receives a large array of gene results and uses `useMemo` to: filter by significance threshold, sort by selected column, compute summary statistics (mean HR, significant count), and paginate. Support column header click to change sort.
**Starter code**:
```typescript
interface GeneTableProps {
  genes: GeneSurvivalResponse[];
  significanceThreshold: number;
  pageSize: number;
}

// TODO: Create GeneTable with:
//   1. useState for sortColumn, sortDirection, currentPage
//   2. useMemo for filtered genes (p_value < threshold)
//   3. useMemo for sorted genes (by sortColumn/sortDirection)
//   4. useMemo for paginated slice
//   5. useMemo for summary stats (count, mean HR, min p-value)
//   6. Clickable column headers to toggle sort
//   7. Pagination controls (prev/next/page numbers)
```
**Test criteria**:
- Filtering/sorting/pagination recalculate only when inputs change
- Sort toggles direction on repeated click, pagination resets on filter change
**Key concepts**: useMemo, dependency arrays, derived state, sorting, pagination

### Exercise 6: Compound Component Pattern
**Task**: Create a `DataPanel` compound component with `DataPanel.Header`, `DataPanel.Body`, `DataPanel.Footer`, and `DataPanel.Stat` subcomponents. Use React Context internally to share panel state (collapsed, theme). Support collapsible behavior.
**Starter code**:
```typescript
// TODO: Define PanelContext with isCollapsed, toggle, theme
// TODO: Create DataPanel as parent with Provider
// TODO: Create DataPanel.Header with collapse toggle button
// TODO: Create DataPanel.Body that hides when collapsed
// TODO: Create DataPanel.Footer always visible
// TODO: Create DataPanel.Stat for key-value pairs (label, value, color)
```
**Test criteria**:
- Subcomponents access shared context, collapse toggles body visibility
- Stat renders with correct color coding, components compose naturally
**Key concepts**: Compound components, React Context, composition, forwardRef
