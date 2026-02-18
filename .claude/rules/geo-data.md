---
paths:
  - "backend/app/**/*geo*"
  - "backend/app/**/*gene_mapping*"
---

# GEO Data Rules

Rules for working with NCBI GEO (Gene Expression Omnibus) data.

## Dataset Types

- **GSE (Series)**: Collection of samples - primary target
- **GSM (Sample)**: Individual sample with expression values
- **GPL (Platform)**: Microarray platform with probe annotations

## Rate Limiting

NCBI enforces strict limits: 3 req/s without API key, 10 req/s with key.
Always add delay: `await asyncio.sleep(0.34)` between requests.

## Probe to Gene Mapping

1. Get platform annotation (GPL file)
2. Map probe IDs → gene symbols
3. Aggregate multiple probes per gene (mean)
4. Drop or warn on missing mappings

## Metadata Detection

| Column Type | Patterns to Match |
|-------------|-------------------|
| Time | `survival`, `os_time`, `rfs_time`, `follow_up`, `months`, `days` |
| Event | `status`, `event`, `dead`, `death`, `recurrence`, `os_status` |

## Common Issues

| Issue | Solution |
|-------|----------|
| 429 Too Many Requests | Add delay, use API key |
| Missing gene symbols | Try alternative annotation source |
| Mismatched samples | Verify sample IDs align between matrix and metadata |

## URL Patterns

```python
f"https://ftp.ncbi.nlm.nih.gov/geo/series/{gse_id[:5]}nnn/{gse_id}/matrix/{gse_id}_series_matrix.txt.gz"
f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{gpl_id[:4]}nnn/{gpl_id}/annot/{gpl_id}.annot.gz"
```
