# pandas Exercises

Exercises for bioinformatics data manipulation, based on patterns from the backend services.

## Beginner

### Exercise 1: Create and Filter a DataFrame
**Task**: Create a gene expression DataFrame from raw data, filter by expression threshold and statistical significance, sort by p-value, and return top N genes.
**Starter code**:
```python
import pandas as pd

def create_gene_df(gene_data: list[dict]) -> pd.DataFrame:
    # TODO: Create DataFrame from list of dicts
    #   Expected keys: gene_symbol, expression, p_value, hazard_ratio
    # TODO: Filter rows where p_value < 0.05
    # TODO: Sort by p_value ascending
    # TODO: Return top 20 rows
    return pd.DataFrame()
```
**Test criteria**:
- DataFrame has correct columns and dtypes
- Only significant genes returned, sorted by p_value, max 20 rows
**Key concepts**: DataFrame creation, boolean filtering, sort_values, head

### Exercise 2: Handle Missing Values
**Task**: Clean a clinical data DataFrame: drop rows where `time` or `event` is missing, fill missing `age` with median, fill missing `stage` with "Unknown", and convert `event` to int type.
**Starter code**:
```python
def clean_clinical_data(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: Drop rows where 'time' or 'event' is NaN
    # TODO: Fill 'age' NaN with median age
    # TODO: Fill 'stage' NaN with "Unknown"
    # TODO: Convert 'event' column to int
    # TODO: Return cleaned DataFrame
    return df
```
**Test criteria**:
- No NaN in time/event columns, age filled with median
- Stage filled with "Unknown", event is int dtype
**Key concepts**: dropna, fillna, median, astype, subset parameter

## Intermediate

### Exercise 3: GroupBy with Aggregation
**Task**: Given a multi-dataset gene results DataFrame, group by gene_symbol across datasets. Compute: mean hazard_ratio, min p_value, count of datasets, and consistency score (fraction of datasets where direction matches the majority direction).
**Starter code**:
```python
def aggregate_gene_results(results_df: pd.DataFrame) -> pd.DataFrame:
    # results_df columns: gene_symbol, dataset, hazard_ratio, p_value, direction
    # TODO: Group by gene_symbol
    # TODO: Aggregate: mean HR, min p-value, dataset count
    # TODO: Calculate consistency score per gene
    # TODO: Sort by consistency desc, then p_value asc
    return pd.DataFrame()
```
**Test criteria**:
- One row per gene, correct mean HR and min p-value
- Consistency = fraction of datasets matching majority direction
**Key concepts**: groupby, agg, custom aggregation functions, sort_values

### Exercise 4: Merge Expression and Clinical Data
**Task**: Merge a gene expression matrix (genes x samples) with clinical metadata (samples x clinical variables). Handle mismatched sample IDs, verify alignment, and return a combined DataFrame ready for survival analysis.
**Starter code**:
```python
def merge_expression_clinical(
    expression: pd.DataFrame,  # genes (rows) x samples (columns)
    clinical: pd.DataFrame,    # samples (rows) x clinical variables
) -> pd.DataFrame:
    # TODO: Transpose expression to samples x genes
    # TODO: Find common samples between expression columns and clinical index
    # TODO: Align both DataFrames to common samples
    # TODO: Merge on sample index
    # TODO: Verify 'time' and 'event' columns exist in result
    # TODO: Return combined DataFrame
    return pd.DataFrame()
```
**Test criteria**:
- Only common samples included, alignment verified
- Result has both expression and clinical columns
**Key concepts**: transpose, index intersection, merge/join, alignment

## Advanced

### Exercise 5: Vectorized Gene Expression Normalization
**Task**: Implement log2 normalization, quantile normalization, and z-score standardization for a gene expression matrix. All operations should be vectorized (no loops).
**Starter code**:
```python
import numpy as np

def log2_normalize(expression: pd.DataFrame) -> pd.DataFrame:
    # TODO: Apply log2(x + 1) transformation, handle zeros
    return expression

def quantile_normalize(expression: pd.DataFrame) -> pd.DataFrame:
    # TODO: Rank each column, compute mean across rows for each rank
    # TODO: Replace ranked values with mean values
    return expression

def zscore_normalize(expression: pd.DataFrame) -> pd.DataFrame:
    # TODO: Per-gene (row) z-score: (x - mean) / std
    # TODO: Handle genes with zero std (replace with 0)
    return expression
```
**Test criteria**:
- log2: no negative values, zeros handled correctly
- quantile: all columns have identical distributions
- zscore: each row has mean~0 and std~1, zero-std handled
**Key concepts**: Vectorized operations, broadcasting, rank, numpy integration

### Exercise 6: Probe-to-Gene Mapping Pipeline
**Task**: Map probe IDs in an expression matrix to gene symbols using a platform annotation table. Handle many-to-one mappings (average expression), unknown probes (drop), and case-insensitive matching.
**Starter code**:
```python
def map_probes_to_genes(
    expression: pd.DataFrame,   # probes x samples
    annotation: pd.DataFrame,   # columns: probe_id, gene_symbol
) -> pd.DataFrame:
    # TODO: Clean annotation: strip whitespace, uppercase gene symbols
    # TODO: Remove rows with missing or "---" gene symbols
    # TODO: Merge expression index with annotation on probe_id
    # TODO: For duplicate gene symbols: average expression across probes
    # TODO: Set gene_symbol as index
    # TODO: Return genes x samples matrix
    return pd.DataFrame()
```
**Test criteria**:
- Unmapped probes dropped, duplicates averaged
- Case-insensitive matching, "---" treated as missing
**Key concepts**: merge, groupby mean, index manipulation, string cleaning
