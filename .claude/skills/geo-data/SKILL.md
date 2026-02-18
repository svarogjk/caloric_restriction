---
name: geo-data
description: NCBI GEO (Gene Expression Omnibus) data handling patterns. Use when fetching datasets, parsing expression matrices, mapping probe IDs to gene symbols, or extracting clinical metadata.
---

# GEO Data Handling

## Dataset Types

- **GSE (Series)**: Collection of samples from an experiment
- **GSM (Sample)**: Individual sample with expression values
- **GPL (Platform)**: Microarray platform with probe annotations
- **GDS (Dataset)**: Curated dataset (subset of GSE)

## API Patterns

### Searching GEO

```python
async def search_geo(query: str, organism: str = "Homo sapiens", max_results: int = 100) -> list[dict]:
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = {
        "db": "gds",
        "term": f"{query} AND {organism}[Organism] AND gse[Entry Type]",
        "retmax": max_results,
        "retmode": "json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/esearch.fcgi", params=params)
        data = response.json()
        return data["esearchresult"]["idlist"]
```

### Downloading Expression Matrix

```python
async def download_series_matrix(gse_id: str) -> pd.DataFrame:
    url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{gse_id[:5]}nnn/{gse_id}/matrix/{gse_id}_series_matrix.txt.gz"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    content = gzip.decompress(response.content).decode('utf-8')
    lines = content.split('\n')
    data_start = next(i for i, line in enumerate(lines) if line.startswith('"ID_REF"') or line.startswith('ID_REF'))
    return pd.read_csv(StringIO('\n'.join(lines[data_start:])), sep='\t', index_col=0)
```

## Probe to Gene Mapping

```python
def map_probes_to_genes(expression_df: pd.DataFrame, annotation_df: pd.DataFrame,
                        probe_col: str = 'ID', gene_col: str = 'Gene Symbol') -> pd.DataFrame:
    mapping = annotation_df.set_index(probe_col)[gene_col].to_dict()
    expression_df['gene'] = expression_df.index.map(mapping)
    expression_df = expression_df.dropna(subset=['gene'])
    return expression_df.groupby('gene').mean()
```

## Metadata Extraction

```python
def detect_survival_columns(metadata: pd.DataFrame) -> dict:
    survival_patterns = {
        'time': ['survival', 'os_time', 'rfs_time', 'dfs_time', 'pfs_time', 'follow_up', 'months', 'days', 'years'],
        'event': ['status', 'event', 'dead', 'death', 'recurrence', 'relapse', 'progression', 'os_status']
    }
    detected = {'time': None, 'event': None}
    for col in metadata.columns:
        col_lower = col.lower()
        for col_type, patterns in survival_patterns.items():
            if any(p in col_lower for p in patterns):
                detected[col_type] = col
                break
    return detected
```

## Rate Limiting

NCBI rate limits: 3 requests/second without API key, 10 with key.

```python
class GEOClient:
    def __init__(self, api_key: str | None = None):
        self.delay = 0.1 if api_key else 0.34

    async def fetch_with_rate_limit(self, url: str) -> httpx.Response:
        await asyncio.sleep(self.delay)
        async with httpx.AsyncClient() as client:
            return await client.get(url)
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 429 Too Many Requests | Rate limit exceeded | Add delay, use API key |
| Missing gene symbols | Platform lacks annotation | Try alternative annotation source |
| Mismatched samples | Matrix vs metadata mismatch | Verify sample IDs align |
| Empty expression values | Failed download | Retry with different URL format |
