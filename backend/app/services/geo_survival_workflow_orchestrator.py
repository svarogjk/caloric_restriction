"""
GEO Survival Analysis Workflow Orchestrator
Integrates all services to provide end-to-end survival analysis on GEO data
Identifies genes associated with survival/lifespan across multiple datasets
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import Counter
import pandas as pd

from app.services.geo_client import GEOClient, GEODataset, GEOSearchResult
from app.services.geo_ranking_service import GEODatasetRankingService
from app.services.geo_loader_service import GEODataLoaderService
from app.services.survival_analysis_service import (
    SurvivalAnalysisService,
    SurvivalAnalysisResult,
    GeneSurvivalResult
)
from app.config.logging_config import get_logger

logger = get_logger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class GeneSurvivalOccurrence:
    """Track gene survival associations across datasets"""
    
    gene_id: str
    gene_symbol: Optional[str]
    n_datasets: int
    avg_hazard_ratio: float
    avg_cox_p_value: float
    avg_log_rank_p_value: float
    datasets: List[str]
    risk_direction_consistency: float  # 0-1, how consistent is high_risk/low_risk
    predominant_risk: str  # "high_risk" or "low_risk"
    # Per-dataset detailed results
    per_dataset_results: List[Dict[str, Any]] = None


@dataclass
class CrossDatasetSurvivalAnalysis:
    """Results from survival analysis across multiple datasets"""

    query: str
    n_datasets_analyzed: int
    n_datasets_with_survival: int
    common_survival_genes: List[GeneSurvivalOccurrence]
    all_survival_results: List[SurvivalAnalysisResult]
    processing_time: float
    timestamp: datetime
    # Ranking service feedback for user
    ranking_quality_score: Optional[float] = None
    ranking_recommendations: Optional[str] = None


class GEOSurvivalWorkflowOrchestrator:
    """
    Orchestrates complete GEO survival analysis workflow:
    1. Search GEO for relevant datasets (cancer, aging, clinical studies)
    2. Rank datasets by survival analysis potential
    3. Load expression data and detect survival metadata
    4. Perform survival analysis (Cox regression, Kaplan-Meier)
    5. Identify genes commonly associated with survival
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        model: str = "mistral",
    ):
        """Initialize all services
        
        Args:
            api_key: Optional GEO API key
            email: Optional email for GEO API
            model: LLM model to use ('mistral' or 'claude')
        """
        self.geo_client = GEOClient(api_key=api_key, email=email)
        self.ranking_service = GEODatasetRankingService(model=model)
        self.loader_service = GEODataLoaderService(model=model)
        self.survival_service = SurvivalAnalysisService(
            p_value_threshold=0.05,
            hazard_ratio_threshold=1.5,
            min_samples_per_group=5,
            model=model
        )
        self.current_model = model
    
    async def analyze_query(
        self,
        query: str,
        max_datasets: int = 10,
        organism: Optional[str] = None,  # None allows both human and mouse
        min_occurrence: int = 2,
        model: Optional[str] = None,
        ranking_multiplier: int = 3,
    ) -> CrossDatasetSurvivalAnalysis:
        """
        Complete survival analysis workflow for a query
        
        Args:
            query: Search query (e.g., "cancer survival prognosis")
            max_datasets: Maximum datasets to analyze
            organism: Filter by organism (None for any)
            min_occurrence: Minimum datasets where gene must appear
            model: LLM model to use ('mistral' or 'claude')
            ranking_multiplier: Multiplier for datasets to rank before analysis
        
        Returns:
            CrossDatasetSurvivalAnalysis with survival-associated genes
        """
        start_time = datetime.now()
        
        use_model = model if model else self.current_model
        logger.info(f"Starting GEO survival analysis workflow for: {query} with model: {use_model}")
        
        # Update services to use the specified model
        if model and model != self.current_model:
            self.ranking_service.set_model(model)
            self.loader_service.set_model(model)
            self.survival_service.set_model(model)
            self.current_model = model
        
        # Step 1: Search GEO for datasets with survival/clinical data
        search_result = await self._search_geo(query, organism, max_datasets, ranking_multiplier)
        
        if not search_result.datasets:
            logger.warning("No datasets found from search")
            return self._create_empty_result(query, start_time)
        
        logger.info(f"Found {len(search_result.datasets)} datasets")
        
        # Step 2: Rank datasets
        datasets_for_ranking = min(len(search_result.datasets), max_datasets * ranking_multiplier)
        ranked_datasets, ranking_quality, ranking_recommendations = await self._rank_datasets(
            search_result.datasets, query, datasets_for_ranking
        )

        top_datasets = ranked_datasets[:max_datasets]
        logger.info(f"Ranked {datasets_for_ranking} datasets, analyzing top {len(top_datasets)}")

        # Step 3: Pre-load platform mappings
        await self._preload_platforms(top_datasets)

        # Step 4: Load and analyze each dataset for survival
        survival_results = await self._analyze_datasets_survival(top_datasets)

        logger.info(f"Completed survival analysis on {len(survival_results)} datasets")

        # Step 5: Identify common survival-associated genes
        common_genes = self._find_common_survival_genes(survival_results, min_occurrence) if survival_results else []

        logger.info(f"Found {len(common_genes)} genes associated with survival across datasets")

        processing_time = (datetime.now() - start_time).total_seconds()

        return CrossDatasetSurvivalAnalysis(
            query=query,
            n_datasets_analyzed=len(ranked_datasets),
            n_datasets_with_survival=len(survival_results),
            common_survival_genes=common_genes,
            all_survival_results=survival_results,
            processing_time=processing_time,
            timestamp=datetime.now(),
            ranking_quality_score=ranking_quality,
            ranking_recommendations=ranking_recommendations
        )
    
    async def _search_geo(
        self,
        query: str,
        organism: Optional[str],
        max_results: int,
        search_multiplier: int = 3
    ) -> GEOSearchResult:
        """Search GEO for datasets with survival/clinical data"""
        
        # Add survival-related keywords to improve search
        survival_keywords = self._extract_keywords(query)
        
        try:
            logger.info(f"Searching GEO with keywords: {survival_keywords}")
            
            # Search for both microarray and RNA-seq datasets
            # First try expression profiling by array (microarray) - more reliable for series matrix
            # Request more results than needed since many won't have actual survival data
            result_array = await self.geo_client.search(
                keywords=survival_keywords,
                max_results=max_results * search_multiplier,
                organism=organism,
                dataset_type="Expression profiling by array"
            )
            
            # Also search for RNA-seq datasets (fewer as they often need supplementary files)
            result_rnaseq = await self.geo_client.search(
                keywords=survival_keywords,
                max_results=max_results,
                organism=organism,
                dataset_type="Expression profiling by high throughput sequencing"
            )
            
            # Combine results, removing duplicates
            seen_accessions = set()
            combined_datasets = []
            
            for dataset in result_array.datasets + result_rnaseq.datasets:
                if dataset.accession not in seen_accessions:
                    seen_accessions.add(dataset.accession)
                    combined_datasets.append(dataset)
            
            total_count = result_array.total_count + result_rnaseq.total_count
            
            result = GEOSearchResult(
                datasets=combined_datasets,
                total_count=total_count,
                search_query=result_array.search_query,
                timestamp=datetime.now()
            )
            
            logger.info(f"GEO search completed. Found {result.total_count} total, {len(result.datasets)} retrieved (array: {len(result_array.datasets)}, RNA-seq: {len(result_rnaseq.datasets)})")
            return result
        
        except Exception as e:
            logger.error(f"GEO search failed: {type(e).__name__}: {e}")
            return GEOSearchResult(
                datasets=[],
                total_count=0,
                search_query=query,
                timestamp=datetime.now()
            )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract search keywords from query and add survival-related terms based on query type"""
        common_words = {'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'and', 'or', 
                       'what', 'which', 'how', 'does', 'do', 'is', 'are', 'genes', 'gene',
                       'predict', 'affect', 'associated', 'with'}
        query_lower = query.lower()
        words = query_lower.split()
        keywords = [w for w in words if w not in common_words and len(w) > 2]
        
        # Detect query type: cancer, aging/CR, or other
        is_mouse_study = any(w in query_lower for w in ['mouse', 'mice', 'lifespan', 'aging', 'longevity', 'caloric restriction'])
        
        # Detect specific cancer types for better search targeting
        cancer_types = {
            'breast': ['breast cancer', 'breast carcinoma', 'breast tumor'],
            'lung': ['lung cancer', 'lung carcinoma', 'lung adenocarcinoma', 'NSCLC', 'SCLC'],
            'colorectal': ['colorectal cancer', 'colon cancer', 'rectal cancer', 'CRC'],
            'hepatocellular': ['hepatocellular carcinoma', 'liver cancer', 'HCC'],
            'gastric': ['gastric cancer', 'stomach cancer', 'gastric carcinoma'],
            'pancreatic': ['pancreatic cancer', 'pancreatic adenocarcinoma', 'PDAC'],
            'ovarian': ['ovarian cancer', 'ovarian carcinoma'],
            'prostate': ['prostate cancer', 'prostate carcinoma'],
            'glioma': ['glioma', 'glioblastoma', 'GBM', 'brain tumor'],
            'leukemia': ['leukemia', 'AML', 'CLL', 'ALL'],
            'lymphoma': ['lymphoma', 'DLBCL', 'hodgkin'],
            'melanoma': ['melanoma', 'skin cancer'],
        }
        
        detected_cancer = None
        for cancer_key, cancer_terms in cancer_types.items():
            for term in cancer_terms:
                if term.lower() in query_lower:
                    detected_cancer = cancer_key
                    break
            if detected_cancer:
                break
        
        is_cancer_study = detected_cancer is not None or 'cancer' in query_lower or 'carcinoma' in query_lower
        
        if is_mouse_study:
            # For mouse/aging studies, look for lifespan/longevity data
            survival_keywords = [
                "lifespan",
                "longevity", 
                "survival curve",
                "median survival",
                "age at death",
            ]
            logger.info(f"Query type: mouse/aging study")
        elif is_cancer_study:
            # For cancer studies, prioritize datasets with ACTUAL survival data
            # Key insight: Include terms that indicate the dataset CONTAINS survival metadata
            # These terms are more likely to appear in datasets with actual clinical follow-up
            survival_keywords = [
                "overall survival",
                "survival analysis",  # Datasets that did survival analysis likely have data
                "clinical outcome",   # Clinical outcome data typically includes survival
                "patient outcome",    # Patient outcomes = survival/events
                "prognostic",         # Prognostic studies have survival data
                "clinical data",      # General clinical data inclusion
                "follow-up",          # Indicates longitudinal data collection
            ]
            # Add specific cancer terms to ensure we get the right cancer type
            if detected_cancer:
                cancer_search_terms = cancer_types[detected_cancer][:2]  # Top 2 terms for this cancer
                keywords = cancer_search_terms + keywords  # Put cancer type first
            logger.info(f"Query type: cancer study (detected: {detected_cancer or 'general'})")
        else:
            # General clinical studies
            survival_keywords = [
                "overall survival",
                "survival time",
                "clinical outcome",
                "patient cohort",
                "follow-up",
                "survival analysis",
            ]
            logger.info(f"Query type: general clinical study")
        
        # Combine user keywords with survival keywords
        # User keywords first (especially cancer type), then survival keywords
        combined = keywords[:4] + survival_keywords
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in combined:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        logger.info(f"Search keywords: {unique_keywords[:8]}")
        return unique_keywords[:8]
    
    async def _rank_datasets(
        self,
        datasets: List[GEODataset],
        query: str,
        top_k: int
    ) -> Tuple[List[GEODataset], Optional[float], Optional[str]]:
        """
        Rank datasets by survival analysis potential

        Returns:
            Tuple of (ranked_datasets, quality_score, recommendations)
        """

        try:
            result = await self.ranking_service.rank_datasets(
                datasets=datasets,
                query=query,
                top_k=top_k
            )
            return result.datasets, result.quality_score, result.recommendations

        except Exception as e:
            logger.error(f"Dataset ranking failed: {e}")
            return datasets[:top_k], None, None
    
    async def _preload_platforms(self, datasets: List[GEODataset]) -> None:
        """Pre-load all platform mappings"""
        
        if not datasets:
            return
        
        platform_ids = set()
        for dataset in datasets:
            if dataset.platforms:
                for platform_id in dataset.platforms:
                    if platform_id and isinstance(platform_id, str):
                        platform_ids.add(platform_id)
        
        if not platform_ids:
            return
        
        platform_ids = list(platform_ids)
        logger.info(f"Pre-loading {len(platform_ids)} platform mappings")
        
        try:
            await self.loader_service.gene_mapping_service.get_batch_probe_to_gene_mappings(
                platform_ids=platform_ids,
                use_cache=True
            )
            logger.info("Successfully pre-loaded platform mappings")
        except Exception as e:
            logger.warning(f"Error pre-loading platforms: {e}")
    
    async def _analyze_datasets_survival(
        self,
        datasets: List[GEODataset]
    ) -> List[SurvivalAnalysisResult]:
        """Load and analyze datasets for survival associations"""
        
        semaphore = asyncio.Semaphore(1)
        
        async def process_dataset(dataset: GEODataset) -> Optional[SurvivalAnalysisResult]:
            async with semaphore:
                logger.info(f"Processing dataset for survival: {dataset.accession}")
                
                try:
                    # Load data
                    loaded_data = await self.loader_service.load_dataset(
                        dataset=dataset,
                        use_cache=True,
                        normalize=True
                    )
                    
                    if loaded_data is None:
                        logger.warning(f"Failed to load {dataset.accession}")
                        return None
                    
                    if not hasattr(loaded_data, 'expression_matrix') or loaded_data.expression_matrix is None:
                        logger.warning(f"Dataset {dataset.accession} has no expression_matrix")
                        return None
                    
                    logger.info(f"Loaded data for {dataset.accession}")
                    
                    # Quality checks
                    n_samples = len(loaded_data.expression_matrix.columns)
                    if n_samples < 10:  # Need more samples for survival analysis
                        logger.warning(f"Dataset {dataset.accession} has too few samples ({n_samples}) for survival analysis")
                        return None
                    
                    n_genes = len(loaded_data.expression_matrix)
                    if n_genes < 100:
                        logger.warning(f"Dataset {dataset.accession} has too few genes ({n_genes})")
                        return None
                    
                    # Check gene mapping
                    if not loaded_data.probe_to_gene_mapping or len(loaded_data.probe_to_gene_mapping) == 0:
                        logger.warning(f"Dataset {dataset.accession} - gene mapping failed")
                        return None
                    
                    # Perform survival analysis
                    survival_result = await self.survival_service.analyze_survival(
                        loaded_data=loaded_data
                    )
                    
                    if survival_result is None:
                        logger.warning(f"No survival data found in {dataset.accession}")
                        return None
                    
                    if survival_result.n_significant_genes > 0:
                        logger.info(f"  Found {survival_result.n_significant_genes} survival-associated genes")
                        return survival_result
                    else:
                        logger.warning(f"  No significant survival associations found")
                        return None
                
                except Exception as e:
                    logger.error(f"Error processing {dataset.accession}: {e}")
                    return None
        
        # Process all datasets
        results = await asyncio.gather(
            *[process_dataset(dataset) for dataset in datasets],
            return_exceptions=False
        )
        
        survival_results = [r for r in results if r is not None]
        
        logger.info(f"Completed survival analysis on {len(survival_results)} datasets")
        
        return survival_results
    
    def _normalize_gene_identifier(self, gene_id: str, gene_symbol: Optional[str]) -> Tuple[str, Optional[str]]:
        """
        Normalize gene identifier for cross-dataset comparison.

        Returns:
            Tuple of (normalized_identifier, display_symbol)
        """
        # If we have a valid gene symbol, use it (normalized to uppercase)
        if gene_symbol and not gene_symbol.isdigit():
            # Check if it's a real gene symbol (not a probe ID pattern)
            if not any(x in gene_symbol for x in ['_at', '_s_at', '_x_at', 'AFFX-']):
                normalized = gene_symbol.upper().strip()
                return normalized, gene_symbol

        # Check if gene_id itself looks like a gene symbol (not numeric, not probe-like)
        if gene_id and not gene_id.isdigit():
            # Skip probe ID patterns
            if not any(x in gene_id for x in ['_at', '_s_at', '_x_at', 'AFFX-', '_PM', '_MM']):
                # Looks like a gene symbol
                normalized = gene_id.upper().strip()
                return normalized, gene_id

        # Fall back to the original gene_id (might be Entrez ID or probe ID)
        return gene_id, gene_symbol

    def _find_common_survival_genes(
        self,
        survival_results: List[SurvivalAnalysisResult],
        min_occurrence: int
    ) -> List[GeneSurvivalOccurrence]:
        """Identify genes commonly associated with survival across datasets"""

        gene_data = {}

        for result in survival_results:
            for gene in result.significant_genes:
                # Normalize gene identifier for consistent cross-dataset matching
                gene_identifier, display_symbol = self._normalize_gene_identifier(
                    gene.gene_id, gene.gene_symbol
                )

                if gene_identifier not in gene_data:
                    gene_data[gene_identifier] = {
                        'symbol': display_symbol or gene.gene_symbol,
                        'datasets': [],
                        'hazard_ratios': [],
                        'cox_p_values': [],
                        'log_rank_p_values': [],
                        'risk_directions': [],
                        'per_dataset_results': [],
                    }
                
                # Skip if this dataset has already been processed for this gene (prevents duplicates)
                if result.accession in gene_data[gene_identifier]['datasets']:
                    logger.warning(f"Duplicate entry detected for gene {gene_identifier} in dataset {result.accession} - skipping")
                    continue
                
                gene_data[gene_identifier]['datasets'].append(result.accession)
                gene_data[gene_identifier]['hazard_ratios'].append(gene.hazard_ratio)
                gene_data[gene_identifier]['cox_p_values'].append(gene.cox_p_value)
                gene_data[gene_identifier]['log_rank_p_values'].append(gene.log_rank_p_value)
                gene_data[gene_identifier]['risk_directions'].append(gene.expression_direction)
                
                # Store per-dataset result for meta-analysis
                per_dataset_entry = {
                    'dataset_id': result.accession,
                    'dataset_title': result.title,
                    'hazard_ratio': gene.hazard_ratio,
                    'hazard_ratio_ci_lower': gene.hazard_ratio_ci_lower,
                    'hazard_ratio_ci_upper': gene.hazard_ratio_ci_upper,
                    'cox_p_value': gene.cox_p_value,
                    'log_rank_p_value': gene.log_rank_p_value,
                    'risk_direction': gene.expression_direction,
                    'n_samples': gene.n_samples_high + gene.n_samples_low,
                    'median_survival_high': gene.median_survival_high,
                    'median_survival_low': gene.median_survival_low,
                }
                
                # Include KM curve data if available
                if gene.km_curve_high:
                    per_dataset_entry['km_curve_high'] = {
                        'times': gene.km_curve_high.times,
                        'survival_probabilities': gene.km_curve_high.survival_probabilities,
                        'ci_lower': gene.km_curve_high.ci_lower,
                        'ci_upper': gene.km_curve_high.ci_upper,
                        'n_samples': gene.km_curve_high.n_samples,
                        'n_events': gene.km_curve_high.n_events,
                    }
                if gene.km_curve_low:
                    per_dataset_entry['km_curve_low'] = {
                        'times': gene.km_curve_low.times,
                        'survival_probabilities': gene.km_curve_low.survival_probabilities,
                        'ci_lower': gene.km_curve_low.ci_lower,
                        'ci_upper': gene.km_curve_low.ci_upper,
                        'n_samples': gene.km_curve_low.n_samples,
                        'n_events': gene.km_curve_low.n_events,
                    }
                
                gene_data[gene_identifier]['per_dataset_results'].append(per_dataset_entry)
        
        # Filter by minimum occurrence
        common_genes = []
        
        for gene_identifier, data in gene_data.items():
            n_datasets = len(data['datasets'])
            
            if n_datasets >= min_occurrence:
                avg_hr = sum(data['hazard_ratios']) / len(data['hazard_ratios'])
                avg_cox_p = sum(data['cox_p_values']) / len(data['cox_p_values'])
                avg_lr_p = sum(data['log_rank_p_values']) / len(data['log_rank_p_values'])
                
                # Calculate risk direction consistency
                risk_counts = Counter(data['risk_directions'])
                max_risk_count = max(risk_counts.values())
                risk_consistency = max_risk_count / n_datasets
                predominant_risk = risk_counts.most_common(1)[0][0]
                
                common_genes.append(GeneSurvivalOccurrence(
                    gene_id=gene_identifier,
                    gene_symbol=data['symbol'],
                    n_datasets=n_datasets,
                    avg_hazard_ratio=avg_hr,
                    avg_cox_p_value=avg_cox_p,
                    avg_log_rank_p_value=avg_lr_p,
                    datasets=data['datasets'],
                    risk_direction_consistency=risk_consistency,
                    predominant_risk=predominant_risk,
                    per_dataset_results=data['per_dataset_results']
                ))
        
        # Sort by number of datasets and then by average p-value
        common_genes.sort(key=lambda x: (-x.n_datasets, x.avg_cox_p_value))
        
        logger.info(f"Found {len(common_genes)} common survival-associated genes")
        
        if common_genes:
            sample_genes = common_genes[:10]
            logger.info("Top survival-associated genes:")
            for gene in sample_genes:
                logger.info(f"  {gene.gene_id}: {gene.n_datasets} datasets, HR={gene.avg_hazard_ratio:.2f}, "
                          f"p={gene.avg_cox_p_value:.2e}, risk={gene.predominant_risk} ({gene.risk_direction_consistency:.0%})")
        
        return common_genes
    
    def _create_empty_result(
        self,
        query: str,
        start_time: datetime
    ) -> CrossDatasetSurvivalAnalysis:
        """Create empty result when no datasets found"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return CrossDatasetSurvivalAnalysis(
            query=query,
            n_datasets_analyzed=0,
            n_datasets_with_survival=0,
            common_survival_genes=[],
            all_survival_results=[],
            processing_time=processing_time,
            timestamp=datetime.now()
        )
    
    def export_survival_genes(
        self,
        analysis: CrossDatasetSurvivalAnalysis,
        output_path: str,
        top_n: Optional[int] = None
    ):
        """Export survival-associated genes to CSV"""
        
        genes = analysis.common_survival_genes
        if top_n:
            genes = genes[:top_n]
        
        data = []
        for gene in genes:
            data.append({
                'gene_id': gene.gene_id,
                'gene_symbol': gene.gene_symbol,
                'n_datasets': gene.n_datasets,
                'avg_hazard_ratio': gene.avg_hazard_ratio,
                'avg_cox_p_value': gene.avg_cox_p_value,
                'avg_log_rank_p_value': gene.avg_log_rank_p_value,
                'predominant_risk': gene.predominant_risk,
                'risk_consistency': gene.risk_direction_consistency,
                'datasets': ','.join(gene.datasets)
            })
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} survival genes to {output_path}")
    
    async def close(self):
        """Close all services"""
        await self.geo_client.close()
        await self.loader_service.close()


# Example usage
async def example_workflow():
    """Example of complete survival analysis workflow"""
    
    orchestrator = GEOSurvivalWorkflowOrchestrator(
        email="svarogjk1989@gmail.com",
        model="mistral"
    )
    
    try:
        # Run survival analysis
        result = await orchestrator.analyze_query(
            query="cancer survival prognosis gene expression",
            max_datasets=5,
            organism="Homo sapiens",  # Human for cancer survival
            min_occurrence=2
        )
        
        print("\n=== GEO Survival Analysis Results ===")
        print(f"Query: {result.query}")
        print(f"Datasets analyzed: {result.n_datasets_analyzed}")
        print(f"Datasets with survival data: {result.n_datasets_with_survival}")
        print(f"Processing time: {result.processing_time:.1f}s")
        print("\nTop 20 Survival-Associated Genes:")
        print(f"{'Gene':<15} {'Datasets':<10} {'Hazard Ratio':<15} {'P-value':<12} {'Risk':<12}")
        print("-" * 70)
        
        for gene in result.common_survival_genes[:20]:
            print(f"{gene.gene_id:<15} {gene.n_datasets:<10} "
                  f"{gene.avg_hazard_ratio:>14.2f} {gene.avg_cox_p_value:>11.2e} {gene.predominant_risk:<12}")
        
        # Export results
        orchestrator.export_survival_genes(
            result,
            "/tmp/survival_genes.csv",
            top_n=100
        )
        
    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(example_workflow())
