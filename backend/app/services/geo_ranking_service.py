"""
GEO Dataset Ranking Service
Uses LLM to rank datasets by differential expression analysis potential
Similar architecture to paper_ranking_service.py
"""

import logging
from typing import List, Dict, Any, Optional
import json
import asyncio

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from app.models.llm_models import model_dict
from app.services.geo_client import GEODataset
from app.services.gene_mapping_service import GeneMappingService

logger = logging.getLogger(__name__)


class DatasetScore(BaseModel):
    """Score for a single dataset"""
    
    accession: str
    diff_expr_score: float = Field(
        ge=0, le=10,
        description="Score 0-10 for differential expression analysis potential"
    )
    rationale: str = Field(description="Brief explanation of score")


class RankedDatasets(BaseModel):
    """Ranked list of datasets"""
    
    datasets: List[DatasetScore]
    overall_quality: float = Field(
        ge=0, le=10,
        description="Overall quality of dataset collection"
    )
    recommendations: str = Field(description="Recommendations for improving results")


class GEODatasetRankingService:
    """
    Service for AI-powered GEO dataset ranking
    Focuses on differential expression analysis potential
    Includes platform size as a ranking factor (smaller is better, single platform preferred)
    """
    
    def __init__(self, model: str = "mistral"):
        """Initialize ranking agent"""
        self.model = model
        self.gene_mapping_service = GeneMappingService()
        self._platform_size_cache: Dict[str, Optional[float]] = {}
        
        self.ranking_agent = Agent(
            model=model_dict.get(self.model, model_dict["mistral"]),
            output_type=RankedDatasets,
            system_prompt=self._get_system_prompt(),
            retries=2,
        )
    
    def set_model(self, model: str) -> None:
        """Update the model used by the ranking agent"""
        self.model = model
        self.ranking_agent = Agent(
            model=model_dict.get(self.model, model_dict["mistral"]),
            output_type=RankedDatasets,
            system_prompt=self._get_system_prompt(),
            retries=2,
        )
        logger.info(f"Updated ranking service to use model: {model}")
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for dataset ranking"""
        return """You are an expert at identifying GEO datasets suitable for differential expression analysis.

            Evaluate each dataset based on:

            HIGH SCORE (8-10):
            - Clear treatment vs control comparison
            - Adequate sample sizes (n>=3 per group)
            - RNA-seq or microarray expression profiling
            - Well-defined experimental design
            - Relevant organism and intervention type
            - Mentions statistical analysis or DEG identification
            - Uses single, smaller platform (preferred over multiple large platforms)

            MEDIUM SCORE (5-7):
            - Some comparison groups mentioned
            - Moderate sample sizes
            - Expression profiling data type
            - Less clear experimental design
            - May lack explicit control group
            - Moderate platform size or multiple platforms

            LOW SCORE (0-4):
            - Single condition or time series only
            - Very small sample sizes (n<3)
            - Non-expression data types (ChIP-seq, methylation)
            - Unclear experimental design
            - No mention of comparative analysis
            - Very large or many different platforms

            Note: Platform size matters - smaller platforms and single platforms are preferable to multiple large platforms.
            Be realistic and conservative. Not all GEO datasets are suitable for differential expression."""
    
    async def rank_datasets(
        self,
        datasets: List[GEODataset],
        query: str,
        top_k: int = 20
    ) -> List[GEODataset]:
        """
        Rank datasets by differential expression potential and platform size.
        Smaller platforms and single platforms are preferred.
        
        Args:
            datasets: Datasets to rank
            query: Original search query
            top_k: Number of top datasets to return
        
        Returns:
            Re-ranked list of datasets, sorted by LLM score + platform size penalty
        """
        if not datasets:
            logger.warning("No datasets to rank")
            return []
        
        logger.info(f"Ranking {len(datasets)} datasets for query: {query}")
        
        max_datasets_for_llm = min(len(datasets), 50)
        dataset_summaries = await self._prepare_dataset_summaries(datasets[:max_datasets_for_llm])
        
        ranking_prompt = self._build_ranking_prompt(query, dataset_summaries)
        
        try:
            result = await self.ranking_agent.run(ranking_prompt)
            ranked = result.output
            
            logger.info(f"Datasets ranked successfully")
            logger.info(f"  Overall quality: {ranked.overall_quality:.1f}/10")
            logger.info(f"  Top dataset score: {ranked.datasets[0].diff_expr_score:.1f}/10")
            
            reordered = await self._reorder_datasets(datasets, ranked.datasets)
            
            return reordered[:top_k]
        
        except Exception as e:
            logger.error(f"Dataset ranking failed: {e}")
            return datasets[:top_k]
    
    async def _prepare_dataset_summaries(self, datasets: List[GEODataset]) -> List[Dict[str, Any]]:
        """Prepare dataset summaries for LLM, including platform size information"""
        summaries = []
        
        for dataset in datasets:
            summary_text = (
                dataset.summary[:400] if dataset.summary 
                else "No summary available"
            )
            
            # Fetch platform sizes for all platforms in this dataset
            platform_sizes = []
            total_size_mb = 0.0
            
            if dataset.platforms:
                for platform in dataset.platforms:
                    size_mb = await self.gene_mapping_service.get_platform_size_mb(platform)
                    if size_mb is not None:
                        platform_sizes.append({"platform": platform, "size_mb": round(size_mb, 1)})
                        total_size_mb += size_mb
                    else:
                        platform_sizes.append({"platform": platform, "size_mb": "unknown"})
            
            # Create platform description for LLM
            platform_description = ""
            if platform_sizes:
                if len(platform_sizes) == 1:
                    ps = platform_sizes[0]
                    if isinstance(ps["size_mb"], float):
                        platform_description = f"Single platform ({ps['platform']}, {ps['size_mb']:.0f}MB)"
                    else:
                        platform_description = f"Single platform ({ps['platform']}, {ps['size_mb']})"
                else:
                    size_str = ", ".join([f"{p['platform']} ({p['size_mb']}MB)" for p in platform_sizes])
                    platform_description = f"Multiple platforms ({len(platform_sizes)}): {size_str}"
            
            summary = {
                "accession": dataset.accession,
                "title": dataset.title,
                "summary": summary_text,
                "organism": dataset.organism,
                "sample_count": dataset.sample_count,
                "dataset_type": dataset.dataset_type,
                "platforms": dataset.platforms,
                "platform_info": platform_description,
                "total_platform_size_mb": round(total_size_mb, 1) if total_size_mb > 0 else "unknown",
                "num_platforms": len(dataset.platforms)
            }
            summaries.append(summary)
        
        return summaries
    
    def _build_ranking_prompt(
        self,
        query: str,
        dataset_summaries: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for dataset ranking, including platform size considerations"""
        
        prompt = f"""Query: {query}

Datasets to evaluate and rank (score 0-10 for differential expression potential):

{json.dumps(dataset_summaries, indent=2)}

For each dataset:
1. Score from 0-10 based on suitability for differential expression analysis
2. Provide brief rationale

Consider:
- Experimental design (treatment vs control, multiple groups)
- Sample sizes (adequate replication)
- Data type (RNA-seq or microarray expression)
- Organism relevance to query
- Intervention or condition tested
- Statistical analysis mentioned
- PLATFORM SIZE: Prefer single, smaller platforms over multiple large platforms
  * Single platform dataset = bonus points
  * Each additional platform = small penalty
  * Very large platforms (>1000MB) = penalty (slower downloads, more data to process)
  * Small to medium platforms (<500MB) = preferred

Also provide:
- overall_quality: Average quality of this dataset collection (0-10)
- recommendations: How to improve search if quality is low

Be conservative - only high scores for clearly suitable datasets with reasonable platforms."""
        
        return prompt
    
    async def _reorder_datasets(
        self,
        original_datasets: List[GEODataset],
        scored_datasets: List[DatasetScore]
    ) -> List[GEODataset]:
        """
        Reorder datasets based on LLM scores + platform size penalty.
        Single, smaller platforms get bonuses; multiple large platforms get penalties.
        """
        
        accession_to_dataset = {d.accession: d for d in original_datasets}
        
        # Calculate adjusted scores considering platform size
        dataset_scores = []
        
        for scored in scored_datasets:
            if scored.accession not in accession_to_dataset:
                continue
            
            dataset = accession_to_dataset[scored.accession]
            llm_score = scored.diff_expr_score
            
            # Calculate platform penalty/bonus
            platform_penalty = 0.0
            
            if dataset.platforms:
                num_platforms = len(dataset.platforms)
                
                # Penalty for multiple platforms (each additional platform = -0.3 points)
                if num_platforms > 1:
                    platform_penalty += (num_platforms - 1) * 0.3
                    logger.debug(f"{dataset.accession}: -{(num_platforms - 1) * 0.3:.1f} for {num_platforms} platforms")
                
                # Penalty for very large platforms (>1GB = -0.5, >2GB = -1.0)
                total_size = 0.0
                for platform in dataset.platforms:
                    size_mb = self._platform_size_cache.get(platform)
                    if size_mb is None:
                        # Try to get from cache or fetch
                        size_mb = await self.gene_mapping_service.get_platform_size_mb(platform)
                        if size_mb is not None:
                            self._platform_size_cache[platform] = size_mb
                    
                    if size_mb is not None:
                        total_size += size_mb
                        if size_mb > 2000:  # >2GB
                            platform_penalty += 1.0
                        elif size_mb > 1000:  # >1GB
                            platform_penalty += 0.5
                
                # Bonus for single, small platform (<200MB)
                if num_platforms == 1 and total_size < 200:
                    platform_penalty = -0.5  # Bonus (negative penalty)
                    logger.debug(f"{dataset.accession}: +0.5 bonus for single small platform ({total_size:.0f}MB)")
            
            # Calculate final adjusted score (keep within 0-10 range)
            adjusted_score = max(0.0, min(10.0, llm_score - platform_penalty))
            
            dataset_scores.append({
                "accession": dataset.accession,
                "llm_score": llm_score,
                "platform_adjustment": -platform_penalty,
                "final_score": adjusted_score,
                "dataset": dataset
            })
        
        # Sort by final adjusted score
        sorted_scores = sorted(
            dataset_scores,
            key=lambda x: x["final_score"],
            reverse=True
        )
        
        reordered = [item["dataset"] for item in sorted_scores]
        
        # Log top adjustments
        for item in sorted_scores[:5]:
            if item["platform_adjustment"] != 0:
                logger.debug(
                    f"  {item['accession']}: LLM={item['llm_score']:.1f} → "
                    f"final={item['final_score']:.1f} (platform adj: {item['platform_adjustment']:+.1f})"
                )
        
        # Add datasets that weren't scored by LLM
        scored_accessions = {sd.accession for sd in scored_datasets}
        for dataset in original_datasets:
            if dataset.accession not in scored_accessions:
                reordered.append(dataset)
        
        return reordered