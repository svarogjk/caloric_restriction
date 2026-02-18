# Bug Patterns - Frontend (React/TypeScript)

Bug templates for generating code review exercises. Each pattern includes the buggy code, the fix, and the category.

## Security Bugs

### XSS via dangerouslySetInnerHTML
```typescript
// BUGGY
const MessageContent: React.FC<{ html: string }> = ({ html }) => (
  <div dangerouslySetInnerHTML={{ __html: html }} />
);

// FIX
import DOMPurify from 'dompurify';
const MessageContent: React.FC<{ html: string }> = ({ html }) => (
  <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />
);
```
**Impact**: Renders unsanitized HTML, allowing script injection attacks.

### Token in URL Parameters
```typescript
// BUGGY
const response = await axios.get(`/api/data?token=${token}`);

// FIX
const response = await axios.get('/api/data', {
  headers: { Authorization: `Bearer ${token}` }
});
```
**Impact**: Tokens in URLs appear in browser history, server logs, and referrer headers.

### Storing Sensitive Data in localStorage Without Encryption
```typescript
// BUGGY
localStorage.setItem('user_data', JSON.stringify({ ssn: '123-45-6789', ...user }));

// FIX - only store non-sensitive identifiers
localStorage.setItem('auth_token', token);
```
**Impact**: localStorage is accessible to any JS on the domain, including XSS attacks.

## Logic Bugs

### Stale Closure in useEffect
```typescript
// BUGGY
const [count, setCount] = useState(0);
useEffect(() => {
  const interval = setInterval(() => {
    setCount(count + 1); // Captures initial count = 0
  }, 1000);
  return () => clearInterval(interval);
}, []); // Missing count dependency

// FIX
useEffect(() => {
  const interval = setInterval(() => {
    setCount(prev => prev + 1); // Functional update
  }, 1000);
  return () => clearInterval(interval);
}, []);
```
**Impact**: `count` is captured at 0 in the closure. Always use functional updates for setters in intervals.

### Missing useEffect Cleanup
```typescript
// BUGGY
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws/chat');
  ws.onmessage = (e) => setMessages(prev => [...prev, e.data]);
  // Missing cleanup!
}, []);

// FIX
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws/chat');
  ws.onmessage = (e) => setMessages(prev => [...prev, e.data]);
  return () => ws.close(); // Cleanup on unmount
}, []);
```
**Impact**: WebSocket connection leaks on component unmount, causing memory leaks and ghost updates.

### Incorrect State Update
```typescript
// BUGGY
const handleAddItem = (item: Item) => {
  items.push(item); // Mutating state directly
  setItems(items);   // Same reference, no re-render
};

// FIX
const handleAddItem = (item: Item) => {
  setItems(prev => [...prev, item]); // New array reference
};
```
**Impact**: React doesn't re-render because the array reference is the same. Always create new references.

### Race Condition in Async Effect
```typescript
// BUGGY
useEffect(() => {
  fetchData(query).then(setData);
}, [query]);
// Fast typing: old request may resolve after new one

// FIX
useEffect(() => {
  let cancelled = false;
  fetchData(query).then(result => {
    if (!cancelled) setData(result);
  });
  return () => { cancelled = true; };
}, [query]);
```
**Impact**: Rapid state changes cause stale data to overwrite fresh data.

### Wrong Key Prop in Lists
```typescript
// BUGGY
{genes.map((gene, index) => (
  <GeneCard key={index} gene={gene} />  // Index as key
))}

// FIX
{genes.map((gene) => (
  <GeneCard key={gene.gene_id} gene={gene} />  // Stable unique key
))}
```
**Impact**: Using index as key causes incorrect DOM recycling when items are reordered, added, or removed.

### Async Function in useEffect
```typescript
// BUGGY
useEffect(async () => {  // useEffect can't be async
  const data = await fetchData();
  setData(data);
}, []);

// FIX
useEffect(() => {
  const loadData = async () => {
    const data = await fetchData();
    setData(data);
  };
  loadData();
}, []);
```
**Impact**: useEffect expects void or cleanup function. Async returns a Promise, which breaks cleanup.

## Performance Bugs

### Missing useMemo for Expensive Computation
```typescript
// BUGGY
const Component: React.FC<{ genes: Gene[] }> = ({ genes }) => {
  // Recalculates on every render
  const sortedGenes = genes
    .filter(g => g.p_value < 0.05)
    .sort((a, b) => a.hazard_ratio - b.hazard_ratio);
  return <GeneList genes={sortedGenes} />;
};

// FIX
const Component: React.FC<{ genes: Gene[] }> = ({ genes }) => {
  const sortedGenes = useMemo(() =>
    genes
      .filter(g => g.p_value < 0.05)
      .sort((a, b) => a.hazard_ratio - b.hazard_ratio),
    [genes]
  );
  return <GeneList genes={sortedGenes} />;
};
```
**Impact**: Expensive filtering/sorting runs on every render, even when `genes` hasn't changed.

### Creating Objects in Render
```typescript
// BUGGY
const Chart: React.FC = () => (
  <LineChart data={data}>
    <XAxis label={{ value: 'Time', position: 'bottom' }} /> {/* New object every render */}
  </LineChart>
);

// FIX
const X_LABEL = { value: 'Time', position: 'bottom' } as const;
const Chart: React.FC = () => (
  <LineChart data={data}>
    <XAxis label={X_LABEL} />
  </LineChart>
);
```
**Impact**: New object references on every render cause child components to re-render unnecessarily.

### Unnecessary Re-renders from Inline Callbacks
```typescript
// BUGGY
{genes.map(gene => (
  <GeneCard
    key={gene.gene_id}
    gene={gene}
    onToggle={() => dispatch(expandGene(gene.gene_id))} // New function each render
  />
))}

// FIX
const handleToggle = useCallback((geneId: string) => {
  dispatch(expandGene(geneId));
}, [dispatch]);

{genes.map(gene => (
  <GeneCard
    key={gene.gene_id}
    gene={gene}
    onToggle={() => handleToggle(gene.gene_id)}
  />
))}
```
**Impact**: New function references prevent React.memo optimization on child components.

### Large Import Without Tree Shaking
```typescript
// BUGGY
import _ from 'lodash'; // Imports entire lodash (~70KB)
const result = _.uniq(items);

// FIX
import uniq from 'lodash/uniq'; // Imports only uniq (~1KB)
const result = uniq(items);
// Or better: [...new Set(items)]
```
**Impact**: Bloats bundle size. Import only what you need or use native alternatives.

## Style/Convention Bugs

### Using `any` Type
```typescript
// BUGGY
const handleResponse = (data: any) => {
  setResults(data.genes);
};

// FIX
interface ApiResponse {
  genes: GeneSurvivalResponse[];
  datasets_analyzed: number;
}
const handleResponse = (data: ApiResponse) => {
  setResults(data.genes);
};
```
**Impact**: `any` defeats TypeScript's type safety. Project rules forbid `any` types.

### Missing Error Boundary
```typescript
// BUGGY
const App = () => (
  <div>
    <SearchPage />  {/* If this crashes, entire app goes white */}
  </div>
);

// FIX
const App = () => (
  <ErrorBoundary fallback={<ErrorFallback />}>
    <SearchPage />
  </ErrorBoundary>
);
```
**Impact**: Unhandled render errors crash the entire React tree. Error boundaries contain failures.

### Inline Styles Instead of Tailwind
```typescript
// BUGGY
<div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '16px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>

// FIX
<div className="bg-white rounded-lg p-4 shadow-md">
```
**Impact**: Inline styles bypass Tailwind's design system, cause inconsistency, and increase bundle size.

### Missing Loading State
```typescript
// BUGGY
const SearchPage: React.FC = () => {
  const { results } = useSelector((s: RootState) => s.search);
  return <GeneList genes={results?.genes || []} />;  // No loading indicator
};

// FIX
const SearchPage: React.FC = () => {
  const { results, loading, error } = useSelector((s: RootState) => s.search);
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  return <GeneList genes={results?.genes || []} />;
};
```
**Impact**: Users see empty UI during data fetching with no indication of progress.
