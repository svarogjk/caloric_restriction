---
name: geo-data
description: Use this skill when working with NCBI GEO (Gene Expression Omnibus) data, downloading datasets, parsing expression matrices, or mapping probe IDs to gene symbols.
---

# GEO Data Skill

You are an expert in working with NCBI Gene Expression Omnibus (GEO) data.

## GEO Data Structure

### Dataset Types
- **GSE (Series)**: Collection of samples from an experiment
- **GSM (Sample)**: Individual sample with expression values
- **GPL (Platform)**: Microarray platform with probe annotations
- **GDS (Dataset)**: Curated dataset (subset of GSE)

### Common File Formats
- **Series Matrix**: Tab-delimited expression matrix with metadata header
- **SOFT format**: Structured text with platform annotations
- **Supplementary files**: Raw data in various formats (CEL, TXT, CSV)

## API Patterns

### Searching GEO
```python
import httpx

async def search_geo(
    query: str,
    organism: str = "Homo sapiens",
    max_results: int = 100
) -> list[dict]:
    """Search GEO for datasets matching query."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Search for GSE IDs
    search_url = f"{base_url}/esearch.fcgi"
    params = {
        "db": "gds",
        "term": f"{query} AND {organism}[Organism] AND gse[Entry Type]",
        "retmax": max_results,
        "retmode": "json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(search_url, params=params)
        data = response.json()
        return data["esearchresult"]["idlist"]
```

### Fetching Dataset Metadata
```python
async def fetch_dataset_info(gse_id: str) -> dict:
    """Fetch metadata for a GEO series."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params = {
        "db": "gds",
        "id": gse_id,
        "retmode": "json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        return response.json()["result"][gse_id]
```

### Downloading Expression Matrix
```python
import gzip
from io import StringIO

async def download_series_matrix(gse_id: str) -> pd.DataFrame:
    """Download and parse series matrix file."""
    url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{gse_id[:5]}nnn/{gse_id}/matrix/{gse_id}_series_matrix.txt.gz"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    # Decompress and parse
    content = gzip.decompress(response.content).decode('utf-8')

    # Find data start (skip metadata lines starting with !)
    lines = content.split('\n')
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith('"ID_REF"') or line.startswith('ID_REF'):
            data_start = i
            break

    # Parse expression matrix
    data_text = '\n'.join(lines[data_start:])
    df = pd.read_csv(StringIO(data_text), sep='\t', index_col=0)

    return df
```

## Probe to Gene Mapping

### Platform Annotation
```python
async def get_platform_annotation(gpl_id: str) -> pd.DataFrame:
    """Download platform annotation for probe-to-gene mapping."""
    url = f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{gpl_id[:4]}nnn/{gpl_id}/annot/{gpl_id}.annot.gz"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    content = gzip.decompress(response.content).decode('utf-8')

    # Parse annotation (skip # comment lines)
    lines = [l for l in content.split('\n') if not l.startswith('#')]
    df = pd.read_csv(StringIO('\n'.join(lines)), sep='\t')

    return df

def map_probes_to_genes(
    expression_df: pd.DataFrame,
    annotation_df: pd.DataFrame,
    probe_col: str = 'ID',
    gene_col: str = 'Gene Symbol'
) -> pd.DataFrame:
    """Map probe IDs to gene symbols and aggregate."""
    # Create probe-to-gene mapping
    mapping = annotation_df.set_index(probe_col)[gene_col].to_dict()

    # Map and aggregate (mean of probes per gene)
    expression_df['gene'] = expression_df.index.map(mapping)
    expression_df = expression_df.dropna(subset=['gene'])
    expression_df = expression_df.groupby('gene').mean()

    return expression_df
```

## Metadata Extraction

### Clinical Data Parsing
```python
def extract_sample_metadata(series_matrix_content: str) -> pd.DataFrame:
    """Extract sample characteristics from series matrix."""
    metadata = {}

    for line in series_matrix_content.split('\n'):
        if line.startswith('!Sample_'):
            key = line.split('\t')[0].replace('!Sample_', '')
            values = line.split('\t')[1:]
            # Clean quoted values
            values = [v.strip('"') for v in values]
            metadata[key] = values

    return pd.DataFrame(metadata)

def detect_survival_columns(metadata: pd.DataFrame) -> dict:
    """Detect survival-related columns in metadata."""
    survival_patterns = {
        'time': ['survival', 'os_time', 'rfs_time', 'dfs_time', 'pfs_time',
                 'follow_up', 'months', 'days', 'years'],
        'event': ['status', 'event', 'dead', 'death', 'recurrence',
                  'relapse', 'progression', 'os_status']
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

NCBI has rate limits. Always add delays between requests:

```python
import asyncio

class GEOClient:
    def __init__(self, api_key: str | None = None):
        # With API key: 10 requests/second
        # Without: 3 requests/second
        self.delay = 0.1 if api_key else 0.34
        self.api_key = api_key

    async def fetch_with_rate_limit(self, url: str) -> httpx.Response:
        await asyncio.sleep(self.delay)
        async with httpx.AsyncClient() as client:
            params = {}
            if self.api_key:
                params['api_key'] = self.api_key
            return await client.get(url, params=params)
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 429 Too Many Requests | Rate limit exceeded | Add delay, use API key |
| Missing gene symbols | Platform lacks annotation | Try alternative annotation source |
| Mismatched samples | Matrix vs metadata mismatch | Verify sample IDs align |
| Empty expression values | Failed download | Retry with different URL format |
