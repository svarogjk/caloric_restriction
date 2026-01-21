---
agent: agent
---

# Code Generation Instructions

Follow these rules when generating code for this project:

## Must Do
1. **Type hints** on all Python function signatures
2. **Async/await** for I/O operations (API calls, file reads)
3. **Pydantic models** for data validation
4. **TypeScript interfaces** for all component props
5. **Specific exceptions** only - never bare `try/except`

## Must Not
1. **No bare try/except** - catch specific exceptions or don't use try/except
2. **No standalone .md files** - documentation goes in code or existing files
3. **No `any` types** in TypeScript
4. **No hardcoded secrets** - use environment variables

## Code Examples

### Python Service Method
```python
async def analyze_gene(
    self,
    gene_symbol: str,
    expression_data: pd.DataFrame,
    survival_data: pd.DataFrame,
) -> GeneSurvivalResult:
    """Analyze survival association for a single gene."""
    # Implementation
```

### React Component
```typescript
interface Props {
  gene: GeneData;
  onSelect: (id: string) => void;
}

export const GeneItem: React.FC<Props> = ({ gene, onSelect }) => {
  return <div onClick={() => onSelect(gene.id)}>{gene.symbol}</div>;
};
```

### Exception Handling
```python
# Correct - specific exceptions
try:
    data = await client.fetch(dataset_id)
except httpx.HTTPStatusError as e:
    logger.error(f"HTTP error fetching {dataset_id}: {e.response.status_code}")
    raise
except httpx.TimeoutException:
    logger.warning(f"Timeout fetching {dataset_id}")
    return None
```
