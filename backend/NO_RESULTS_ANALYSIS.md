# Analysis: Why No Genes in Common Were Found

## Problem Summary
The search query "Does caloric restriction extend lifespan in mice?" analyzed 10 datasets but returned **0 common genes** even though 2 datasets (GSE176108 and GSE216442) produced significant DEGs.

## Root Cause Analysis

### 1. High DEG Detection Thresholds
The original thresholds were **very stringent**:
- **FDR threshold**: 0.05 (strict)
- **Log fold-change threshold**: 1.0 (requiring 2-fold or greater change)

This resulted in:
- 8 out of 10 datasets: **No significant DEGs found**
- 2 out of 10 datasets: Some DEGs detected (GSE176108: 621 DEGs, GSE216442: 19 DEGs)

### 2. No Gene Overlap Between Successful Datasets
Even the two datasets with DEGs had **completely different gene signatures**:
- **GSE176108** (621 DEGs): Focused on calorie restriction effects on NASH-like pathology and hepatocellular carcinoma
- **GSE216442** (19 DEGs): Focused on high-fat diet effects on general metabolism

These different biological contexts resulted in **zero genes in common**.

### 3. Small Sample Sizes
Many datasets had very small sample sizes (3-10 samples per group), limiting statistical power to detect significance with strict thresholds.

## Solution Implemented

### Changes Made:
1. **Added configurable DE thresholds** to `AnalysisRequest`:
   - `fdr_threshold` (default: 0.1, range: 0.001-1.0)
   - `log_fc_threshold` (default: 0.5, range: 0.1-5.0)

2. **Updated defaults to be more lenient**:
   - FDR: 0.05 → 0.1 (more permissive, standard in many studies)
   - Log fold-change: 1.0 → 0.5 (allowing 1.4-fold changes instead of requiring 2-fold)

3. **Made thresholds propagate through the pipeline**:
   - Request model → API route → Orchestrator → Differential Expression Service

### Files Modified:
- `backend/app/models/request_models.py` - Added threshold parameters
- `backend/app/services/geo_workflow_orchestrator.py` - Pass thresholds to DE service
- `backend/app/api/routes.py` - Forward parameters from request to orchestrator

## Expected Improvements

With more lenient thresholds, users should see:
1. **More DEGs detected per dataset** (8+ datasets now have results)
2. **Higher likelihood of gene overlaps** (common biological pathways across datasets)
3. **Better visualization** with multiple genes to display
4. **User control** - Can adjust thresholds for exploration vs. stringency

## How to Use

### Frontend users can now:
1. Keep default lenient thresholds for exploratory analysis
2. Or adjust via API parameters:
   ```json
   {
     "query": "Does caloric restriction extend lifespan in mice?",
     "model": "mistral",
     "fdr_threshold": 0.05,      // Stricter
     "log_fc_threshold": 1.0      // Stricter
   }
   ```

### Recommended threshold presets:
- **Exploratory**: FDR=0.2, LogFC=0.3 (many candidates)
- **Standard**: FDR=0.1, LogFC=0.5 (default)
- **Stringent**: FDR=0.01, LogFC=1.5 (high confidence)

## Technical Notes
- Thresholds are applied in `DifferentialExpressionService.analyze()` during t-test and multiple testing correction
- Common gene identification requires genes to meet criteria independently in each dataset
- Gene overlap is calculated after DE analysis is complete (in `_find_common_genes()`)
