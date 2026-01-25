# GEO Data Rules

Rules for working with NCBI GEO (Gene Expression Omnibus) data.

## Dataset Types

- **GSE (Series)**: Collection of samples from an experiment - primary target
- **GSM (Sample)**: Individual sample with expression values
- **GPL (Platform)**: Microarray platform with probe annotations
- **GDS (Dataset)**: Curated dataset (subset of GSE)

## Rate Limiting

NCBI enforces strict rate limits. Always respect them:

```python
# Without API key: 3 requests/second (0.34s delay)
# With API key: 10 requests/second (0.1s delay)
await asyncio.sleep(0.34)  # Default safe delay
```

## Probe to Gene Mapping

Always map probes to gene symbols before analysis:

1. Get platform annotation (GPL file)
2. Map probe IDs to gene symbols
3. Aggregate multiple probes per gene (use mean)
4. Handle missing mappings (drop or warn)

## Metadata Detection

When parsing clinical metadata, look for survival columns:

| Column Type | Patterns to Match |
|-------------|-------------------|
| Time | `survival`, `os_time`, `rfs_time`, `follow_up`, `months`, `days` |
| Event | `status`, `event`, `dead`, `death`, `recurrence`, `os_status` |

## Common Issues

| Issue | Solution |
|-------|----------|
| 429 Too Many Requests | Add delay between requests, use API key |
| Missing gene symbols | Try alternative annotation source |
| Mismatched samples | Verify sample IDs align between matrix and metadata |
| Compressed files | Use gzip.decompress() for .gz files |

## URL Patterns

```python
# Series matrix
f"https://ftp.ncbi.nlm.nih.gov/geo/series/{gse_id[:5]}nnn/{gse_id}/matrix/{gse_id}_series_matrix.txt.gz"

# Platform annotation
f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{gpl_id[:4]}nnn/{gpl_id}/annot/{gpl_id}.annot.gz"
```
