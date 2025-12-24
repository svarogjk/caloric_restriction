"""
GEO Dataset Ranking Service
Uses LLM to rank datasets by survival analysis potential
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
    survival_score: float = Field(
        ge=0, le=10,
        description="Score 0-10 for survival analysis potential"
    )
    rationale: str = Field(description="Brief explanation of score")


class RankedDatasets(BaseModel):
    """Ranked list of datasets"""
    
    datasets: List[DatasetScore]
    overall_quality: float = Field(
        ge=0, le=10,
        description="Overall quality of dataset collection for survival analysis"
    )
    recommendations: str = Field(description="Recommendations for improving results")


class GEODatasetRankingService:
    """
    Service for AI-powered GEO dataset ranking
    Focuses on survival analysis potential (clinical outcomes, time-to-event data)
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
        """Get system prompt for dataset ranking focused on survival analysis"""
        return """You are an expert at identifying GEO datasets suitable for SURVIVAL ANALYSIS.

            CRITICAL: Survival analysis requires ACTUAL NUMERIC DATA in the dataset:
            - A TIME column (survival time, follow-up time, days to death, lifespan)
            - An EVENT column (death/alive status, event indicator, censoring status)
            
            Just mentioning "survival" in the study description is NOT enough.
            The dataset metadata MUST contain actual survival endpoint data.

            HIGH SCORE (8-10) - HAS SURVIVAL DATA:
            The dataset description MUST indicate:
            - "survival time", "follow-up time", "days/months to death/event"
            - "Kaplan-Meier analysis performed" or "Cox regression"
            - "survival data available" or "clinical outcomes included"
            - For mouse studies: "lifespan data", "survival curves", "age at death recorded"
            - Sample size n >= 30 with survival follow-up

            MEDIUM SCORE (5-7) - LIKELY HAS SURVIVAL DATA:
            - Cancer cohorts explicitly mentioning "survival outcome data"
            - Prognostic studies with "patient follow-up data"
            - Aging studies with "lifespan measurements"

            LOW SCORE (0-4) - NO SURVIVAL DATA:
            - Cell line studies (score 0-1) - cells don't have survival
            - Single timepoint tissue samples without follow-up
            - Treatment response without survival endpoints
            - Mechanistic studies without clinical outcomes
            - Studies that just *study* a disease but don't track patient survival
            - Mouse studies without lifespan/survival tracking

            CRITICAL DISTINCTION:
            - "Study of cancer survival pathways" = LOW (studying biology, not patients)
            - "Cancer cohort with 5-year survival follow-up" = HIGH (actual patient survival data)
            - "Caloric restriction study" = LOW (unless explicitly says lifespan tracked)
            - "CR study with lifespan extension data" = HIGH (actual survival data)

            Be VERY STRICT - score 8-10 ONLY if survival endpoint DATA is clearly present."""
    
    async def rank_datasets(
        self,
        datasets: List[GEODataset],
        query: str,
        top_k: int = 20
    ) -> List[GEODataset]:
        """
        Rank datasets by survival analysis potential and platform size.
        Smaller platforms and single platforms are preferred.
        
        Args:
            datasets: Datasets to rank
            query: Original search query
            top_k: Number of top datasets to return
            min_survival_score: Minimum survival score to include (default 5.0)
        
        Returns:
            Re-ranked list of datasets, sorted by LLM score + platform size penalty
            Only includes datasets with survival_score >= min_survival_score
        """
        if not datasets:
            logger.warning("No datasets to rank")
            return []
        
        logger.info(f"Ranking {len(datasets)} datasets for survival analysis potential, query: {query}")
        
        max_datasets_for_llm = min(len(datasets), 50)
        dataset_summaries = await self._prepare_dataset_summaries(datasets[:max_datasets_for_llm])
        
        ranking_prompt = self._build_ranking_prompt(query, dataset_summaries)
        
        try:
            result = await self.ranking_agent.run(ranking_prompt)
            ranked = result.output
            
            logger.info(f"Datasets ranked successfully for survival analysis")
            logger.info(f"  Overall quality: {ranked.overall_quality:.1f}/10")
            logger.info(f"  LLM recommendations: {ranked.recommendations}")
            
            # Log score distribution
            score_counts = {"high (8-10)": 0, "medium (5-7)": 0, "low (0-4)": 0}
            for ds in ranked.datasets:
                if ds.survival_score >= 8:
                    score_counts["high (8-10)"] += 1
                elif ds.survival_score >= 5:
                    score_counts["medium (5-7)"] += 1
                else:
                    score_counts["low (0-4)"] += 1
            logger.info(f"  Score distribution: {score_counts}")
            
            if ranked.datasets:
                logger.info(f"  Top dataset: {ranked.datasets[0].accession} (score: {ranked.datasets[0].survival_score:.1f})")
                logger.info(f"  Top rationale: {ranked.datasets[0].rationale[:200]}")
            
            reordered = await self._reorder_datasets(datasets, ranked.datasets)
            
            # Filter to only datasets with survival score >= 5.0
            min_survival_score = 5.0
            filtered = []
            for dataset in reordered:
                # Find the score for this dataset
                for scored in ranked.datasets:
                    if scored.accession == dataset.accession:
                        if scored.survival_score >= min_survival_score:
                            filtered.append(dataset)
                            logger.info(f"  Including {dataset.accession}: score {scored.survival_score:.1f}")
                        else:
                            logger.debug(f"  Excluding {dataset.accession}: score {scored.survival_score:.1f} < {min_survival_score}")
                        break
            
            if len(filtered) == 0:
                logger.warning(f"No datasets with survival score >= {min_survival_score}. "
                              f"Consider refining search to explicitly include survival/prognosis terms.")
                # Return top-scored datasets anyway for visibility
                return reordered[:top_k]
            
            logger.info(f"  {len(filtered)} datasets passed survival score threshold ({min_survival_score})")
            return filtered[:top_k]
        
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
        """Build prompt for dataset ranking focused on survival analysis potential"""
        
        prompt = f"""Query: {query}

Datasets to evaluate and rank (score 0-10 for SURVIVAL ANALYSIS potential):

{json.dumps(dataset_summaries, indent=2)}

SCORING INSTRUCTIONS - BE VERY STRICT:

SCORE 8-10 (DEFINITELY HAS SURVIVAL DATA):
Must EXPLICITLY mention in title/summary:
- "survival analysis", "overall survival", "OS", "PFS", "RFS", "DFS"
- "Kaplan-Meier", "Cox regression", "hazard ratio"
- "prognosis" AND "outcome" with time component
- "follow-up" with patient outcomes
- Patient cohort with survival/death endpoints

SCORE 5-7 (LIKELY HAS SURVIVAL DATA):
- Cancer cohort mentioning "clinical outcome" or "prognostic"
- Mentions "survival" in context of patient data
- Studies with "time to event" or "progression"

SCORE 0-4 (NO SURVIVAL DATA):
- Cell lines (score 0-1) - NO patient survival possible
- Animal studies without "lifespan" or "longevity" mentioned
- Pure mechanistic/molecular studies
- Treatment studies without outcome follow-up
- No explicit mention of survival/prognosis/outcome

IMPORTANT:
- "Cancer" alone does NOT mean survival data exists
- "Clinical samples" alone does NOT mean survival data exists  
- Must have EXPLICIT survival/outcome endpoints mentioned
- Sample size matters: prefer n >= 50

For each dataset provide:
1. accession: The GEO accession
2. survival_score: Score 0-10 (BE STRICT - most should be 0-4)
3. rationale: Why this score (quote relevant text from summary if survival mentioned)

Also provide:
- overall_quality: Quality of this collection for survival analysis (0-10)
- recommendations: How to improve search for survival datasets"""
        
        return prompt
    
    async def _reorder_datasets(
        self,
        original_datasets: List[GEODataset],
        scored_datasets: List[DatasetScore]
    ) -> List[GEODataset]:
        """
        Reorder datasets based on LLM survival scores + platform size penalty.
        Single, smaller platforms get bonuses; multiple large platforms get penalties.
        """
        
        accession_to_dataset = {d.accession: d for d in original_datasets}
        
        # Calculate adjusted scores considering platform size
        dataset_scores = []
        
        for scored in scored_datasets:
            if scored.accession not in accession_to_dataset:
                continue
            
            dataset = accession_to_dataset[scored.accession]
            llm_score = scored.survival_score
            
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