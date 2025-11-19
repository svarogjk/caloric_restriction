"""
GEO Analysis Workflow Orchestrator
Integrates all services to provide end-to-end GEO data analysis
Identifies commonly altered genes across multiple datasets
"""

import logging
import asyncio
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import Counter
import pandas as pd

from app.services.geo_client import GEOClient, GEODataset, GEOSearchResult
from app.services.geo_ranking_service import GEODatasetRankingService
from app.services.geo_loader_service import GEODataLoaderService
from app.services.differential_expression_service import (
    DifferentialExpressionService,
    DifferentialExpressionResult
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to console/stderr
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class GeneOccurrence:
    """Track gene occurrence across datasets"""
    
    gene_id: str
    n_datasets: int
    avg_log_fc: float
    avg_p_value: float
    avg_adj_p_value: float
    datasets: List[str]
    direction_consistency: float  # 0-1, how consistent is up/down regulation


@dataclass
class CrossDatasetAnalysis:
    """Results from analyzing multiple datasets"""
    
    query: str
    n_datasets_analyzed: int
    n_datasets_with_degs: int
    common_genes: List[GeneOccurrence]
    all_deg_results: List[DifferentialExpressionResult]
    processing_time: float
    timestamp: datetime


class GEOWorkflowOrchestrator:
    """
    Orchestrates complete GEO analysis workflow:
    1. Search GEO for relevant datasets
    2. Rank datasets by DE potential
    3. Load expression data
    4. Perform differential expression
    5. Identify commonly altered genes
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        model: str = "mistral"
    ):
        """Initialize all services"""
        self.geo_client = GEOClient(api_key=api_key, email=email)
        self.ranking_service = GEODatasetRankingService(model=model)
        self.loader_service = GEODataLoaderService(model=model)
        self.de_service = DifferentialExpressionService(
            fdr_threshold=0.05,
            log_fc_threshold=1.0,
            model=model
        )
    
    async def analyze_query(
        self,
        query: str,
        max_datasets: int = 10,
        organism: Optional[str] = "Mus musculus",
        min_occurrence: int = 2,
        model: Optional[str] = None
    ) -> CrossDatasetAnalysis:
        """
        Complete analysis workflow for a query
        
        Args:
            query: Search query (e.g., "caloric restriction aging")
            max_datasets: Maximum datasets to analyze
            organism: Filter by organism
            min_occurrence: Minimum datasets where gene must appear
            model: LLM model to use ('mistral' or 'claude'), defaults to instance model
        
        Returns:
            CrossDatasetAnalysis with common genes
        """
        start_time = datetime.now()
        
        # Use provided model or fall back to instance model
        use_model = model if model else "mistral"  # Default fallback
        logger.info(f"Starting GEO analysis workflow for: {query} with model: {use_model}")
        
        # Update services to use the specified model if different from current
        if model:
            self.ranking_service.set_model(model)
            self.loader_service.set_model(model)
            self.de_service.set_model(model)
        
        # Step 1: Search GEO
        search_result = await self._search_geo(query, organism, max_datasets * 2)
        
        if not search_result.datasets:
            logger.warning("No datasets found")
            return self._create_empty_result(query, start_time)
        
        logger.info(f"Found {len(search_result.datasets)} datasets")
        
        # Step 2: Rank datasets by DE potential
        ranked_datasets = await self._rank_datasets(search_result.datasets, query, max_datasets)
        
        logger.info(f"Ranked and selected top {len(ranked_datasets)} datasets")
        
        # Step 3: Load and analyze each dataset
        deg_results = await self._analyze_datasets(ranked_datasets)
        
        logger.info(f"Completed DE analysis on {len(deg_results)} datasets")
        
        # Step 4: Identify common genes
        common_genes = self._find_common_genes(deg_results, min_occurrence)
        
        logger.info(f"Found {len(common_genes)} genes common across datasets")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return CrossDatasetAnalysis(
            query=query,
            n_datasets_analyzed=len(ranked_datasets),
            n_datasets_with_degs=len(deg_results),
            common_genes=common_genes,
            all_deg_results=deg_results,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
    
    async def _search_geo(
        self,
        query: str,
        organism: Optional[str],
        max_results: int
    ) -> GEOSearchResult:
        """Search GEO for datasets with improved error handling"""
        
        keywords = self._extract_keywords(query)
        
        try:
            logger.info(f"Attempting GEO search with keywords: {keywords}")
            result = await self.geo_client.search(
                keywords=keywords,
                max_results=max_results,
                organism=organism,
                dataset_type="Expression profiling by array"
            )
            logger.info(f"GEO search completed successfully. Found {result.total_count} total results, {len(result.datasets)} datasets retrieved.")
            return result
        
        except Exception as e:
            logger.error(f"GEO search failed after retries: {type(e).__name__}: {e}")
            logger.error(f"Keywords used: {keywords}")
            logger.warning(f"Returning empty results for query: {query}")
            return GEOSearchResult(
                datasets=[],
                total_count=0,
                search_query=query,
                timestamp=datetime.now()
            )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract search keywords from query"""
        # Simple keyword extraction
        common_words = {'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'and', 'or'}
        words = query.lower().split()
        keywords = [w for w in words if w not in common_words and len(w) > 2]
        return keywords[:5]
    
    async def _rank_datasets(
        self,
        datasets: List[GEODataset],
        query: str,
        top_k: int
    ) -> List[GEODataset]:
        """Rank datasets by DE analysis potential"""
        
        try:
            ranked = await self.ranking_service.rank_datasets(
                datasets=datasets,
                query=query,
                top_k=top_k
            )
            return ranked
        
        except Exception as e:
            logger.error(f"Dataset ranking failed: {e}")
            return datasets[:top_k]
    
    async def _analyze_datasets(
        self,
        datasets: List[GEODataset]
    ) -> List[DifferentialExpressionResult]:
        """Load and analyze multiple datasets"""
        
        deg_results = []
        
        for i, dataset in enumerate(datasets):
            logger.info(f"Processing dataset {i+1}/{len(datasets)}: {dataset.accession}")
            
            try:
                # Load data
                loaded_data = await self.loader_service.load_dataset(
                    dataset=dataset,
                    use_cache=True,
                    normalize=True
                )
                
                if loaded_data is None:
                    logger.warning(f"Failed to load {dataset.accession}")
                    continue
                
                logger.info(f"loaded data for {dataset.accession} {dataset.title}")
                
                # Quality check: minimum sample size
                n_samples = len(loaded_data.expression_matrix.columns)
                if n_samples < 4:  # Need at least 2 per group
                    logger.warning(f"Dataset {dataset.accession} has too few samples ({n_samples})")
                    continue
                
                # Quality check: expression data
                n_genes = len(loaded_data.expression_matrix)
                if n_genes < 100:
                    logger.warning(f"Dataset {dataset.accession} has too few genes ({n_genes})")
                    continue
                
                # Perform DE analysis
                de_result = await self.de_service.analyze_differential_expression(
                    loaded_data=loaded_data
                )
                
                if de_result is None:
                    logger.warning(f"Failed DE analysis for {dataset.accession}")
                    continue
                
                if de_result.n_upregulated + de_result.n_downregulated > 0:
                    deg_results.append(de_result)
                    logger.info(f"  Found {de_result.n_upregulated + de_result.n_downregulated} DEGs")
                else:
                    logger.warning("  No significant DEGs found")
            
            except Exception as e:
                logger.error(f"Error processing {dataset.accession}: {e}")
                continue
        
        return deg_results
    
    def _find_common_genes(
        self,
        deg_results: List[DifferentialExpressionResult],
        min_occurrence: int
    ) -> List[GeneOccurrence]:
        """Identify genes commonly altered across datasets"""
        
        # Collect all significant genes
        gene_data = {}  # gene_id -> {datasets: [], log_fcs: [], directions: [], p_values: [], adj_p_values: []}
        
        for result in deg_results:
            significant_degs = [deg for deg in result.deg_genes if deg.is_significant]
            
            for deg in significant_degs:
                gene_id = deg.gene_id
                
                if gene_id not in gene_data:
                    gene_data[gene_id] = {
                        'datasets': [],
                        'log_fcs': [],
                        'directions': [],
                        'p_values': [],
                        'adj_p_values': []
                    }
                
                gene_data[gene_id]['datasets'].append(result.accession)
                gene_data[gene_id]['log_fcs'].append(deg.log_fold_change)
                gene_data[gene_id]['directions'].append(1 if deg.log_fold_change > 0 else -1)
                gene_data[gene_id]['p_values'].append(deg.p_value)
                gene_data[gene_id]['adj_p_values'].append(deg.adj_p_value)
        
        # Filter by minimum occurrence
        common_genes = []
        
        for gene_id, data in gene_data.items():
            n_datasets = len(data['datasets'])
            
            if n_datasets >= min_occurrence:
                avg_log_fc = sum(data['log_fcs']) / len(data['log_fcs'])
                avg_p_value = sum(data['p_values']) / len(data['p_values'])
                avg_adj_p_value = sum(data['adj_p_values']) / len(data['adj_p_values'])
                
                # Calculate direction consistency
                direction_counts = Counter(data['directions'])
                max_direction_count = max(direction_counts.values())
                direction_consistency = max_direction_count / n_datasets
                
                common_genes.append(GeneOccurrence(
                    gene_id=gene_id,
                    n_datasets=n_datasets,
                    avg_log_fc=avg_log_fc,
                    avg_p_value=avg_p_value,
                    avg_adj_p_value=avg_adj_p_value,
                    datasets=data['datasets'],
                    direction_consistency=direction_consistency
                ))
        
        # Sort by number of datasets (descending)
        common_genes.sort(key=lambda x: (x.n_datasets, abs(x.avg_log_fc)), reverse=True)
        
        return common_genes
    
    def _create_empty_result(
        self,
        query: str,
        start_time: datetime
    ) -> CrossDatasetAnalysis:
        """Create empty result when no datasets found"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return CrossDatasetAnalysis(
            query=query,
            n_datasets_analyzed=0,
            n_datasets_with_degs=0,
            common_genes=[],
            all_deg_results=[],
            processing_time=processing_time,
            timestamp=datetime.now()
        )
    
    def export_common_genes(
        self,
        analysis: CrossDatasetAnalysis,
        output_path: str,
        top_n: Optional[int] = None
    ):
        """Export common genes to CSV"""
        
        genes = analysis.common_genes
        if top_n:
            genes = genes[:top_n]
        
        data = []
        for gene in genes:
            data.append({
                'gene_id': gene.gene_id,
                'n_datasets': gene.n_datasets,
                'avg_log_fc': gene.avg_log_fc,
                'direction_consistency': gene.direction_consistency,
                'datasets': ','.join(gene.datasets)
            })
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} common genes to {output_path}")
    
    async def close(self):
        """Close all services"""
        await self.geo_client.close()
        await self.loader_service.close()


# Example usage
async def example_workflow():
    """Example of complete workflow"""
    
    orchestrator = GEOWorkflowOrchestrator(
        email="svarogjk1989@gmail.com",
        model="mistral"
    )
    
    try:
        # Run analysis
        result = await orchestrator.analyze_query(
            query="caloric restriction aging lifespan",
            max_datasets=5,
            organism="Mus musculus",
            min_occurrence=2
        )
        
        print("\n=== GEO Analysis Results ===")
        print(f"Query: {result.query}")
        print(f"Datasets analyzed: {result.n_datasets_analyzed}")
        print(f"Datasets with DEGs: {result.n_datasets_with_degs}")
        print(f"Processing time: {result.processing_time:.1f}s")
        print("\nTop 20 Common Genes:")
        print(f"{'Gene ID':<20} {'Datasets':<10} {'Avg LogFC':<12} {'Direction':<12}")
        print("-" * 60)
        
        for gene in result.common_genes[:20]:
            direction = "Consistent" if gene.direction_consistency > 0.8 else "Variable"
            print(f"{gene.gene_id:<20} {gene.n_datasets:<10} "
                  f"{gene.avg_log_fc:>11.2f} {direction:<12}")
        
        # Export results
        orchestrator.export_common_genes(
            result,
            "/tmp/common_genes.csv",
            top_n=100
        )
        
    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(example_workflow())