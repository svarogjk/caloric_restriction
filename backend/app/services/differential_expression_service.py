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
from pydantic_ai import Agent
from pydantic import BaseModel, Field

from app.services.geo_loader_service import LoadedGEOData

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


# Response model for LLM group detection
class GroupDetectionResponse(BaseModel):
    """Response model for LLM group detection"""
    treatment_sample_ids: List[str] = Field(
        ...,
        description="List of sample IDs identified as treatment/intervention group"
    )
    control_sample_ids: List[str] = Field(
        ...,
        description="List of sample IDs identified as control group"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of how groups were identified"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score for the group detection (0.0-1.0)"
    )


def create_group_detection_agent(model: str = "anthropic") -> Agent:
    """Create LLM agent for group detection with specified model
    
    Args:
        model: Model to use ('anthropic' or 'mistral')
        
    Returns:
        Configured Agent instance
    """
    from app.models.llm_models import model_dict
    
    selected_model = model_dict.get(model)
    if not selected_model:
        logger.warning(f"Unknown model '{model}', defaulting to mistral")
        selected_model = model_dict.get("mistral", model_dict["mistral"])
    
    logger.info(f"Creating group detection agent with model: {model}")
    
    system_prompt = """You are an expert at analyzing GEO dataset metadata to identify experimental groups.

Your task: Identify which samples are treatment/intervention vs control groups.

You MUST return a structured response with:
- treatment_sample_ids: list of sample IDs in treatment group
- control_sample_ids: list of sample IDs in control group  
- reasoning: brief explanation of your decision
- confidence: score 0.0-1.0 for your confidence

Look for keywords in metadata like:
- Treatment/intervention: CR, caloric restriction, drug, treatment, aged, old, HFD, high fat
- Control: control, ad lib, vehicle, placebo, young, CON, normal diet

Return ONLY the structured data, no additional text."""
    
    return Agent(
        model=selected_model,
        output_type=GroupDetectionResponse,
        system_prompt=system_prompt,
        retries=2
    )



@dataclass
class DEGResult:
    """Differential expression result for a single gene"""
    
    gene_id: str  # Original probe ID
    gene_symbol: Optional[str] = None  # Mapped gene symbol (if available)
    log_fold_change: float = 0.0
    p_value: float = 1.0
    adj_p_value: float = 1.0
    mean_treatment: float = 0.0
    mean_control: float = 0.0
    is_significant: bool = False


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
        min_samples_per_group: int = 3,
        model: str = "anthropic"
    ):
        """
        Initialize DE analysis service
        
        Args:
            fdr_threshold: FDR cutoff for significance
            log_fc_threshold: Minimum absolute log fold change
            min_samples_per_group: Minimum samples required per group
            model: LLM model to use for group detection ('anthropic' or 'mistral')
        """
        self.fdr_threshold = fdr_threshold
        self.log_fc_threshold = log_fc_threshold
        self.min_samples_per_group = min_samples_per_group
        self.model = model
        self.group_detection_agent = create_group_detection_agent(model)
    
    def set_model(self, model: str) -> None:
        """Update the model used by the group detection agent"""
        self.model = model
        self.group_detection_agent = create_group_detection_agent(model)
        logger.info(f"Updated differential expression service to use model: {model}")
    
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
            treatment_samples, control_samples = await self._detect_groups(loaded_data)
            
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
        
        # Apply gene symbol mapping if available
        if loaded_data.probe_to_gene_mapping:
            for result in deg_results:
                if result.gene_id in loaded_data.probe_to_gene_mapping:
                    result.gene_symbol = loaded_data.probe_to_gene_mapping[result.gene_id]
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
        
        # Log sample of mapped gene symbols for verification
        if loaded_data.probe_to_gene_mapping:
            sample_degs_with_symbols = [r for r in significant if r.gene_symbol][:10]
            if sample_degs_with_symbols:
                logger.info(f"Sample DEGs with gene symbols for {loaded_data.accession}:")
                for deg in sample_degs_with_symbols:
                    direction = "↑" if deg.log_fold_change > 0 else "↓"
                    logger.info(f"  {direction} {deg.gene_symbol} (probe: {deg.gene_id}, log2FC: {deg.log_fold_change:.2f}, adj_p: {deg.adj_p_value:.2e})")
        
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
    
    async def _detect_groups(
        self,
        loaded_data: LoadedGEOData
    ) -> Tuple[List[str], List[str]]:
        """
        Auto-detect treatment and control groups from metadata using LLM agent with fallback
        
        Returns:
            (treatment_samples, control_samples)
        """
        metadata = loaded_data.sample_metadata
        expr_samples = set(loaded_data.expression_matrix.columns)
        
        if metadata.empty:
            logger.warning("No metadata available for group detection")
            # Fall back to simple split
            samples = list(expr_samples)
            n = len(samples)
            return samples[:n//2], samples[n//2:]
        
        # Ensure metadata index matches expression matrix columns
        metadata = metadata[metadata.index.isin(expr_samples)]
        
        # Try LLM agent first
        try:
            llm_groups = await self._detect_groups_with_llm(metadata, expr_samples)
            if llm_groups:
                treatment_samples, control_samples = llm_groups
                if (len(treatment_samples) >= self.min_samples_per_group and 
                    len(control_samples) >= self.min_samples_per_group):
                    logger.info(f"LLM detected groups: {len(treatment_samples)} treatment, {len(control_samples)} control")
                    return treatment_samples, control_samples
        except Exception as e:
            logger.warning(f"LLM group detection failed, falling back to keyword matching: {e}")
        
        # Fallback: Look for common metadata columns indicating groups
        group_columns = ['characteristics_ch1', 'source_name_ch1', 'title', 'description']
        
        for col in group_columns:
            if col not in metadata.columns:
                continue
                
            values = metadata[col].astype(str)
            
            # Look for treatment keywords
            treatment_keywords = ['treatment', 'cr', 'caloric restriction', 
                                 'restricted', 'drug', 'intervention', 'aged', 'old']
            control_keywords = ['control', 'ad lib', 'ad libitum', 
                               'placebo', 'vehicle', 'wild type', 'wt', 'young']
            
            treatment_mask = values.str.lower().str.contains('|'.join(treatment_keywords), na=False)
            control_mask = values.str.lower().str.contains('|'.join(control_keywords), na=False)
            
            treatment_samples = metadata[treatment_mask].index.tolist()
            control_samples = metadata[control_mask].index.tolist()
            
            # Validate samples exist in expression matrix
            treatment_samples = [s for s in treatment_samples if s in expr_samples]
            control_samples = [s for s in control_samples if s in expr_samples]
            
            if (treatment_samples and control_samples and 
                len(treatment_samples) >= self.min_samples_per_group and
                len(control_samples) >= self.min_samples_per_group):
                logger.info(f"Detected groups from column '{col}' using keyword matching")
                return treatment_samples, control_samples
        
        # If no clear groups found, try to split by unique values
        for col in metadata.columns:
            unique_vals = metadata[col].unique()
            if 2 <= len(unique_vals) <= 3:  # Allow for 2-3 groups to pick the two largest
                # Sort by frequency
                value_counts = metadata[col].value_counts()
                top_2_values = value_counts.head(2).index.tolist()
                
                group1 = metadata[metadata[col] == top_2_values[0]].index.tolist()
                group2 = metadata[metadata[col] == top_2_values[1]].index.tolist() if len(top_2_values) > 1 else []
                
                # Validate samples exist
                group1 = [s for s in group1 if s in expr_samples]
                group2 = [s for s in group2 if s in expr_samples]
                
                if (len(group1) >= self.min_samples_per_group and 
                    len(group2) >= self.min_samples_per_group):
                    logger.info(f"Using binary split from column '{col}'")
                    return group1, group2
        
        logger.warning("Could not reliably detect groups, using simple split")
        samples = list(expr_samples)
        n = len(samples)
        return samples[:n//2], samples[n//2:]
    
    async def _detect_groups_with_llm(
        self,
        metadata: pd.DataFrame,
        expr_samples: set
    ) -> Optional[Tuple[List[str], List[str]]]:
        """
        Use LLM agent to intelligently detect treatment and control groups
        
        Args:
            metadata: Sample metadata DataFrame
            expr_samples: Set of sample IDs in expression matrix
            
        Returns:
            (treatment_samples, control_samples) or None if detection fails
        """
        # Prepare metadata summary for LLM
        metadata_summary = self._prepare_metadata_for_llm(metadata)
        
        try:
            result = await self._run_group_detection_agent(metadata_summary)
            
            if not result:
                return None
            
            # Validate detected samples exist in expression matrix
            treatment_samples = [s for s in result.treatment_sample_ids if s in expr_samples]
            control_samples = [s for s in result.control_sample_ids if s in expr_samples]
            
            logger.info(f"LLM reasoning: {result.reasoning} (confidence: {result.confidence:.2f})")
            
            if treatment_samples and control_samples:
                return treatment_samples, control_samples
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM agent execution failed: {e}")
            return None
    
    async def _run_group_detection_agent(self, metadata_summary: str) -> Optional[GroupDetectionResponse]:
        """Run the group detection agent asynchronously"""
        try:
            prompt = f"""Analyze the following GEO dataset sample metadata and identify treatment and control groups.

Metadata Summary:
{metadata_summary}

Instructions:
1. Identify which samples belong to the TREATMENT/INTERVENTION group
2. Identify which samples belong to the CONTROL group
3. Each group MUST have at least 3 samples
4. Return the sample IDs (like GSM123456) for each group
5. Explain your reasoning briefly

Look for indicators in the metadata:
- Treatment keywords: CR, caloric restriction, treatment, drug, intervention, aged, old, HFD, high fat, DIO
- Control keywords: control, ad lib, ad libitum, placebo, vehicle, young, CON, normal diet, LFD

Return your response in the required structured format."""
            
            result = await self.group_detection_agent.run(prompt)
            
            # Try different ways to extract the structured response from pydantic_ai
            response = None
            
            # Method 1: Try .output attribute (most common in newer versions)
            if hasattr(result, 'output'):
                output = result.output
                if isinstance(output, GroupDetectionResponse):
                    response = output
                elif isinstance(output, dict):
                    # Try to construct from dict
                    try:
                        response = GroupDetectionResponse(**output)
                    except Exception as e:
                        logger.warning(f"Failed to construct from dict: {e}")
                elif isinstance(output, str):
                    # LLM returned text instead of structured output - this shouldn't happen
                    logger.warning(f"LLM returned text instead of structured output: {output[:200]}")
            
            # Method 2: Try .data attribute/method
            if response is None and hasattr(result, 'data'):
                try:
                    data = result.data if not callable(result.data) else result.data()
                    if isinstance(data, GroupDetectionResponse):
                        response = data
                    elif isinstance(data, dict):
                        response = GroupDetectionResponse(**data)
                except (AttributeError, TypeError) as e:
                    logger.debug(f"Could not get data: {e}")
            
            # Method 3: Check if result itself is the response
            if response is None and isinstance(result, GroupDetectionResponse):
                response = result
            
            if response is None:
                logger.warning(f"Could not extract GroupDetectionResponse from result type: {type(result)}")
                if hasattr(result, '__dict__'):
                    logger.debug(f"Result attributes: {result.__dict__.keys()}")
                return None
            
            # Validate the response has required data
            if not response.treatment_sample_ids or not response.control_sample_ids:
                logger.warning(f"LLM returned empty groups: treatment={len(response.treatment_sample_ids)}, control={len(response.control_sample_ids)}")
                return None
            
            return response
            
        except Exception as e:
            logger.warning(f"Group detection agent failed: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _prepare_metadata_for_llm(self, metadata: pd.DataFrame) -> str:
        """
        Prepare metadata in a format suitable for LLM analysis
        
        Args:
            metadata: Sample metadata DataFrame
            
        Returns:
            Formatted string summary of metadata
        """
        summary_lines = []
        summary_lines.append(f"Total samples: {len(metadata)}")
        summary_lines.append(f"Available columns: {', '.join(metadata.columns.tolist())}\n")
        
        # Include key metadata columns
        key_columns = ['characteristics_ch1', 'source_name_ch1', 'title', 'description']
        for col in key_columns:
            if col in metadata.columns:
                summary_lines.append(f"\n{col}:")
                # Sample a few entries from each column
                samples = metadata[col].astype(str).head(min(10, len(metadata)))
                for idx, val in samples.items():
                    summary_lines.append(f"  {idx}: {val[:100]}")  # Truncate long values
        
        return "\n".join(summary_lines)
    
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