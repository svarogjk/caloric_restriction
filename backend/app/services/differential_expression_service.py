"""
Differential Expression Analysis Service
Performs statistical analysis to identify genes altered by interventions
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import warnings

import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

from app.services.geo_loader_service import LoadedGEOData

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


@dataclass
class DEGResult:
    """Differential expression result for a single gene"""
    
    gene_id: str
    log_fold_change: float
    p_value: float
    adj_p_value: float
    mean_treatment: float
    mean_control: float
    is_significant: bool


@dataclass
class DifferentialExpressionResult:
    """Complete differential expression analysis result"""
    
    accession: str
    treatment_group: str
    control_group: str
    n_treatment: int
    n_control: int
    deg_genes: List[DEGResult]
    n_upregulated: int
    n_downregulated: int
    n_total_genes: int
    analysis_method: str
    fdr_threshold: float
    log_fc_threshold: float


class DifferentialExpressionService:
    """
    Service for performing differential expression analysis on GEO data
    """
    
    def __init__(
        self,
        fdr_threshold: float = 0.05,
        log_fc_threshold: float = 1.0,
        min_samples_per_group: int = 3
    ):
        """
        Initialize DE analysis service
        
        Args:
            fdr_threshold: FDR cutoff for significance
            log_fc_threshold: Minimum absolute log fold change
            min_samples_per_group: Minimum samples required per group
        """
        self.fdr_threshold = fdr_threshold
        self.log_fc_threshold = log_fc_threshold
        self.min_samples_per_group = min_samples_per_group
    
    async def analyze_differential_expression(
        self,
        loaded_data: LoadedGEOData,
        treatment_samples: Optional[List[str]] = None,
        control_samples: Optional[List[str]] = None
    ) -> Optional[DifferentialExpressionResult]:
        """
        Perform differential expression analysis
        
        Args:
            loaded_data: Loaded GEO dataset
            treatment_samples: List of treatment sample IDs (auto-detect if None)
            control_samples: List of control sample IDs (auto-detect if None)
        
        Returns:
            DifferentialExpressionResult or None if analysis fails
        """
        logger.info(f"Starting differential expression analysis for {loaded_data.accession}")
        
        # Auto-detect groups if not provided
        if treatment_samples is None or control_samples is None:
            treatment_samples, control_samples = self._detect_groups(loaded_data)
            
            if not treatment_samples or not control_samples:
                logger.error("Could not detect treatment/control groups")
                return None
        
        # Validate group sizes
        if len(treatment_samples) < self.min_samples_per_group:
            logger.error(f"Treatment group too small: {len(treatment_samples)} < {self.min_samples_per_group}")
            return None
        
        if len(control_samples) < self.min_samples_per_group:
            logger.error(f"Control group too small: {len(control_samples)} < {self.min_samples_per_group}")
            return None
        
        logger.info(f"Treatment: {len(treatment_samples)} samples, Control: {len(control_samples)} samples")
        
        # Extract expression data for groups
        expr_matrix = loaded_data.expression_matrix
        
        treatment_expr = expr_matrix[treatment_samples]
        control_expr = expr_matrix[control_samples]
        
        # Perform statistical testing for each gene
        deg_results = []
        
        for gene_id in expr_matrix.index:
            result = self._test_gene(
                gene_id,
                treatment_expr.loc[gene_id],
                control_expr.loc[gene_id]
            )
            if result:
                deg_results.append(result)
        
        if not deg_results:
            logger.error("No genes passed filtering")
            return None
        
        # Multiple testing correction
        p_values = [r.p_value for r in deg_results]
        
        try:
            reject, adj_p_values, _, _ = multipletests(
                p_values,
                method='fdr_bh',
                alpha=self.fdr_threshold
            )
        except Exception as e:
            logger.error(f"FDR correction failed: {e}")
            adj_p_values = p_values
            reject = [p < self.fdr_threshold for p in p_values]
        
        # Update with adjusted p-values
        for i, result in enumerate(deg_results):
            result.adj_p_value = adj_p_values[i]
            result.is_significant = (
                reject[i] and 
                abs(result.log_fold_change) >= self.log_fc_threshold
            )
        
        # Count significant genes
        significant = [r for r in deg_results if r.is_significant]
        n_upregulated = len([r for r in significant if r.log_fold_change > 0])
        n_downregulated = len([r for r in significant if r.log_fold_change < 0])
        
        logger.info(f"Found {len(significant)} significant DEGs: "
                   f"{n_upregulated} up, {n_downregulated} down")
        
        return DifferentialExpressionResult(
            accession=loaded_data.accession,
            treatment_group="treatment",
            control_group="control",
            n_treatment=len(treatment_samples),
            n_control=len(control_samples),
            deg_genes=deg_results,
            n_upregulated=n_upregulated,
            n_downregulated=n_downregulated,
            n_total_genes=len(expr_matrix),
            analysis_method="t-test with FDR correction",
            fdr_threshold=self.fdr_threshold,
            log_fc_threshold=self.log_fc_threshold
        )
    
    def _detect_groups(
        self,
        loaded_data: LoadedGEOData
    ) -> Tuple[List[str], List[str]]:
        """
        Auto-detect treatment and control groups from metadata
        
        Returns:
            (treatment_samples, control_samples)
        """
        metadata = loaded_data.sample_metadata
        
        if metadata.empty:
            logger.warning("No metadata available for group detection")
            # Fall back to simple split
            samples = list(loaded_data.expression_matrix.columns)
            n = len(samples)
            return samples[:n//2], samples[n//2:]
        
        # Look for common metadata columns indicating groups
        group_columns = ['characteristics_ch1', 'source_name_ch1', 'title', 'description']
        
        for col in group_columns:
            if col in metadata.columns:
                values = metadata[col].astype(str)
                
                # Look for treatment keywords
                treatment_keywords = ['treatment', 'cr', 'caloric restriction', 
                                     'restricted', 'drug', 'intervention']
                control_keywords = ['control', 'ad lib', 'ad libitum', 
                                   'placebo', 'vehicle', 'wild type', 'wt']
                
                treatment_mask = values.str.lower().str.contains('|'.join(treatment_keywords))
                control_mask = values.str.lower().str.contains('|'.join(control_keywords))
                
                treatment_samples = metadata[treatment_mask].index.tolist()
                control_samples = metadata[control_mask].index.tolist()
                
                if treatment_samples and control_samples:
                    logger.info(f"Detected groups from column '{col}'")
                    return treatment_samples, control_samples
        
        # If no clear groups found, try to split by unique values
        for col in metadata.columns:
            unique_vals = metadata[col].unique()
            if len(unique_vals) == 2:
                # Assume binary grouping
                group1 = metadata[metadata[col] == unique_vals[0]].index.tolist()
                group2 = metadata[metadata[col] == unique_vals[1]].index.tolist()
                
                if len(group1) >= self.min_samples_per_group and len(group2) >= self.min_samples_per_group:
                    logger.info(f"Using binary split from column '{col}'")
                    return group1, group2
        
        logger.warning("Could not reliably detect groups, using simple split")
        samples = list(loaded_data.expression_matrix.columns)
        n = len(samples)
        return samples[:n//2], samples[n//2:]
    
    def _test_gene(
        self,
        gene_id: str,
        treatment_values: pd.Series,
        control_values: pd.Series
    ) -> Optional[DEGResult]:
        """
        Perform statistical test for a single gene
        
        Args:
            gene_id: Gene identifier
            treatment_values: Expression values in treatment
            control_values: Expression values in control
        
        Returns:
            DEGResult or None if test fails
        """
        # Remove NaN values
        treatment_clean = treatment_values.dropna()
        control_clean = control_values.dropna()
        
        if len(treatment_clean) < 2 or len(control_clean) < 2:
            return None
        
        # Calculate means
        mean_treatment = treatment_clean.mean()
        mean_control = control_clean.mean()
        
        # Calculate log fold change
        # Add small constant to avoid log(0)
        epsilon = 1e-10
        log_fc = np.log2((mean_treatment + epsilon) / (mean_control + epsilon))
        
        # Perform t-test
        try:
            t_stat, p_value = stats.ttest_ind(treatment_clean, control_clean)
            
            # Handle invalid p-values
            if np.isnan(p_value) or np.isinf(p_value):
                p_value = 1.0
        
        except Exception as e:
            logger.debug(f"T-test failed for {gene_id}: {e}")
            return None
        
        return DEGResult(
            gene_id=gene_id,
            log_fold_change=log_fc,
            p_value=p_value,
            adj_p_value=p_value,  # Will be updated later
            mean_treatment=mean_treatment,
            mean_control=mean_control,
            is_significant=False  # Will be updated later
        )
    
    def get_top_degs(
        self,
        result: DifferentialExpressionResult,
        n: int = 50,
        by: str = 'adj_p_value'
    ) -> List[DEGResult]:
        """
        Get top differentially expressed genes
        
        Args:
            result: DE analysis result
            n: Number of top genes to return
            by: Sort by 'adj_p_value' or 'log_fold_change'
        
        Returns:
            List of top DEGResults
        """
        significant = [r for r in result.deg_genes if r.is_significant]
        
        if by == 'adj_p_value':
            sorted_degs = sorted(significant, key=lambda x: x.adj_p_value)
        elif by == 'log_fold_change':
            sorted_degs = sorted(significant, key=lambda x: abs(x.log_fold_change), reverse=True)
        else:
            raise ValueError(f"Unknown sort key: {by}")
        
        return sorted_degs[:n]
    
    def export_results(
        self,
        result: DifferentialExpressionResult,
        output_path: str
    ):
        """Export results to CSV file"""
        
        # Convert to DataFrame
        deg_data = []
        for deg in result.deg_genes:
            deg_data.append({
                'gene_id': deg.gene_id,
                'log_fold_change': deg.log_fold_change,
                'p_value': deg.p_value,
                'adj_p_value': deg.adj_p_value,
                'mean_treatment': deg.mean_treatment,
                'mean_control': deg.mean_control,
                'is_significant': deg.is_significant
            })
        
        df = pd.DataFrame(deg_data)
        df = df.sort_values('adj_p_value')
        
        df.to_csv(output_path, index=False)
        logger.info(f"Exported results to {output_path}")