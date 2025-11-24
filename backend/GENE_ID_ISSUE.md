# Gene ID Issue: Why No Common Genes Are Found

## Problem
When searching for common genes across multiple GEO datasets, the result shows "0 genes in common" even though datasets are successfully analyzed and DEGs are found.

Example from logs:
- GSE176108: 621 DEGs found
- GSE216442: 19 DEGs found
- Common genes: 0

## Root Cause
The current implementation uses **probe IDs** (microarray identifiers) as gene identifiers, not standardized gene symbols:

1. **Microarray data format**:
   - GEO series matrix files contain probe IDs in the first column (ID_REF)
   - Example probe IDs: "1007_s_at", "1053_at", "200000_s_at"
   - These are specific to the microarray platform used in the experiment

2. **The problem**:
   - GSE176108 likely uses **Affymetrix platform** → probe IDs like "1000000_at"
   - GSE216442 likely uses **different platform** → completely different probe IDs
   - Same biological gene may have different probe IDs across platforms
   - Current code directly compares probe IDs → no matches found

3. **Example**:
   ```
   GSE176108 (Affymetrix): Gene "GAPDH" represented as probe "1050_s_at"
   GSE216442 (different): Same gene "GAPDH" represented as probe "229733_at"
   
   Current code: Compares "1050_s_at" vs "229733_at" → NOT equal → no common gene
   Correct approach: Both map to "GAPDH" → Equal → common gene found
   ```

## Solution Required
Map probe IDs to standardized gene symbols before finding common genes:

### Step 1: Get Platform Annotation
- Each GEO dataset has associated platform information
- GEO provides GPL (platform) files with probe ID → gene symbol mappings
- Example: GSE176108 uses GPL1261 (Affymetrix Mouse Genome 430 2.0 Array)

### Step 2: Create Gene Mapping Service
- Fetch GPL files from GEO
- Build probe ID → gene symbol lookup table
- Cache mappings locally

### Step 3: Apply Mapping
- When loading expression data, map probe IDs to gene symbols
- Store both probe ID and gene symbol for reference
- Use gene symbols for finding common genes

### Step 4: Find Common Genes
- Compare gene symbols (not probe IDs)
- Track which datasets/probes represent the same biological gene
- Return common genes with their platform-specific probe IDs for reference

## Implementation Notes

### Affected Files
- `geo_loader_service.py`: Will need to fetch platform annotations and apply mappings
- `differential_expression_service.py`: Already calculates DEGs with probe IDs
- `geo_workflow_orchestrator.py`: `_find_common_genes()` needs to use gene symbols

### Data Sources
- **GEO Platform Files**: `https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL<number>/GPL<number>_family.soft.gz`
- **Alternative**: BioMart/Ensembl for gene ID conversion if GPL files insufficient

### Performance Considerations
- Cache platform annotations locally (once per platform)
- Lazy-load platform data only when needed
- Store mappings in database for future use

## Status
- ✅ Problem identified
- ✅ Gene mapping service created (`GeneMappingService`)
- ✅ Gene mapping integrated into data loader
- ✅ DEGResult updated to include gene symbols
- ✅ _find_common_genes method updated to use gene symbols
- ✅ All tests passing - ready for testing with real queries
