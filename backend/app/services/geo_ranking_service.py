"""
GEO Dataset Ranking Service
Uses LLM to rank datasets by differential expression analysis potential
Similar architecture to paper_ranking_service.py
"""

import logging
from typing import List, Dict, Any
import json

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from app.models.llm_models import model_dict
from app.services.geo_client import GEODataset

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
    """
    
    def __init__(self, model: str = "mistral"):
        """Initialize ranking agent"""
        self.model = model
        
        self.ranking_agent = Agent(
            model=model_dict.get(self.model, model_dict["mistral"]),
            output_type=RankedDatasets,
            system_prompt=self._get_system_prompt(),
            retries=2,
        )
    
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

            MEDIUM SCORE (5-7):
            - Some comparison groups mentioned
            - Moderate sample sizes
            - Expression profiling data type
            - Less clear experimental design
            - May lack explicit control group

            LOW SCORE (0-4):
            - Single condition or time series only
            - Very small sample sizes (n<3)
            - Non-expression data types (ChIP-seq, methylation)
            - Unclear experimental design
            - No mention of comparative analysis

            Be realistic and conservative. Not all GEO datasets are suitable for differential expression."""
    
    async def rank_datasets(
        self,
        datasets: List[GEODataset],
        query: str,
        top_k: int = 20
    ) -> List[GEODataset]:
        """
        Rank datasets by differential expression potential
        
        Args:
            datasets: Datasets to rank
            query: Original search query
            top_k: Number of top datasets to return
        
        Returns:
            Re-ranked list of datasets
        """
        if not datasets:
            logger.warning("No datasets to rank")
            return []
        
        logger.info(f"Ranking {len(datasets)} datasets for query: {query}")
        
        max_datasets_for_llm = min(len(datasets), 50)
        dataset_summaries = self._prepare_dataset_summaries(datasets[:max_datasets_for_llm])
        
        ranking_prompt = self._build_ranking_prompt(query, dataset_summaries)
        
        try:
            result = await self.ranking_agent.run(ranking_prompt)
            ranked = result.output
            
            logger.info(f"Datasets ranked successfully")
            logger.info(f"  Overall quality: {ranked.overall_quality:.1f}/10")
            logger.info(f"  Top dataset score: {ranked.datasets[0].diff_expr_score:.1f}/10")
            
            reordered = self._reorder_datasets(datasets, ranked.datasets)
            
            return reordered[:top_k]
        
        except Exception as e:
            logger.error(f"Dataset ranking failed: {e}")
            return datasets[:top_k]
    
    def _prepare_dataset_summaries(self, datasets: List[GEODataset]) -> List[Dict[str, Any]]:
        """Prepare dataset summaries for LLM"""
        summaries = []
        
        for dataset in datasets:
            summary_text = (
                dataset.summary[:400] if dataset.summary 
                else "No summary available"
            )
            
            summary = {
                "accession": dataset.accession,
                "title": dataset.title,
                "summary": summary_text,
                "organism": dataset.organism,
                "sample_count": dataset.sample_count,
                "dataset_type": dataset.dataset_type,
                "platform": dataset.platform
            }
            summaries.append(summary)
        
        return summaries
    
    def _build_ranking_prompt(
        self,
        query: str,
        dataset_summaries: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for dataset ranking"""
        
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

Also provide:
- overall_quality: Average quality of this dataset collection (0-10)
- recommendations: How to improve search if quality is low

Be conservative - only high scores for clearly suitable datasets."""
        
        return prompt
    
    def _reorder_datasets(
        self,
        original_datasets: List[GEODataset],
        scored_datasets: List[DatasetScore]
    ) -> List[GEODataset]:
        """Reorder datasets based on scores"""
        
        accession_to_dataset = {d.accession: d for d in original_datasets}
        
        reordered = []
        
        for scored in sorted(
            scored_datasets,
            key=lambda x: x.diff_expr_score,
            reverse=True
        ):
            if scored.accession in accession_to_dataset:
                reordered.append(accession_to_dataset[scored.accession])
        
        scored_accessions = {sd.accession for sd in scored_datasets}
        for dataset in original_datasets:
            if dataset.accession not in scored_accessions:
                reordered.append(dataset)
        
        return reordered