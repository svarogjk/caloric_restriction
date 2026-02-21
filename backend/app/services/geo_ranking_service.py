"""
GEO Dataset Ranking Service
Uses LLM to rank datasets by survival analysis potential
Similar architecture to paper_ranking_service.py
"""

import logging
from typing import List, Dict, Any, Optional, Set
import json
import asyncio
import re

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from app.models.llm_models import model_dict
from app.services.geo_client import GEODataset
from app.services.gene_mapping_service import GeneMappingService

logger = logging.getLogger(__name__)

# Known methylation and non-expression array platforms that cannot be used for gene expression survival analysis
# These will be filtered out early to avoid wasting time on them
METHYLATION_PLATFORMS: Set[str] = {
    # Illumina Methylation Arrays
    "GPL13534",   # Illumina HumanMethylation450 BeadChip
    "GPL16791",   # Illumina HumanMethylation450 BeadChip (alternate)
    "GPL17021",   # Illumina HumanMethylation450 BeadChip (alternate)
    "GPL21145",   # Illumina MethylationEPIC BeadChip
    "GPL23976",   # Illumina MethylationEPIC v2.0 BeadChip
    "GPL8490",    # Illumina HumanMethylation27 BeadChip
    # Agilent Methylation
    "GPL14550",   # Agilent Human CpG Island Microarray
    # Affymetrix SNP/Genotyping arrays (not expression)
    "GPL6801",    # Affymetrix SNP Array 6.0
    "GPL3718",    # Affymetrix Mapping 250K
    # Other non-expression platforms
    "GPL24247",   # Illumina MethylationEPIC (often appears in breast cancer datasets)
    "GPL24250",   # Illumina MethylationEPIC
}

# Patterns in platform names that indicate non-expression arrays
NON_EXPRESSION_PATTERNS = [
    r'methylation',
    r'methyl',
    r'epigenetic',
    r'snp\s*array',
    r'genotyping',
    r'copy\s*number',
    r'cnv',
    r'chip-?seq',  # ChIP-seq platforms
    r'mirna',      # miRNA-specific (may or may not want these)
]


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


class RankingResult:
    """Complete ranking result including datasets and metadata"""

    def __init__(
        self,
        datasets: List[GEODataset],
        quality_score: float,
        recommendations: str
    ):
        self.datasets = datasets
        self.quality_score = quality_score
        self.recommendations = recommendations


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
        # Compile non-expression patterns for efficiency
        self._non_expression_regex = re.compile(
            '|'.join(NON_EXPRESSION_PATTERNS), 
            re.IGNORECASE
        )
        # Initialize the ranking agent
        # max_tokens=8192: scoring 25 datasets needs ~2500+ output tokens; 4096 default is too low
        self.ranking_agent = Agent(
            model=model_dict.get(self.model, model_dict["mistral"]),
            output_type=RankedDatasets,
            system_prompt=self._get_system_prompt(),
            retries=2,
            model_settings=ModelSettings(max_tokens=8192),
        )
    
    def _is_methylation_or_non_expression(self, dataset: GEODataset) -> bool:
        """
        Check if a dataset uses a methylation or non-expression platform.
        These datasets cannot be used for gene expression survival analysis.
        
        Returns:
            True if dataset should be skipped (methylation/non-expression)
        """
        # Check platforms against known methylation platforms
        if dataset.platforms:
            for platform in dataset.platforms:
                platform_clean = platform.replace("GPL", "").strip()
                platform_with_prefix = f"GPL{platform_clean}"
                
                if platform_with_prefix in METHYLATION_PLATFORMS:
                    logger.debug(f"{dataset.accession}: Skipping - platform {platform} is methylation array")
                    return True
        
        # Check dataset type for methylation indicators
        if dataset.dataset_type:
            if self._non_expression_regex.search(dataset.dataset_type):
                logger.debug(f"{dataset.accession}: Skipping - dataset type '{dataset.dataset_type}' indicates non-expression")
                return True
        
        # Check title for methylation indicators
        if dataset.title:
            if self._non_expression_regex.search(dataset.title):
                logger.debug(f"{dataset.accession}: Skipping - title indicates methylation/non-expression")
                return True
        
        # Check summary for strong methylation indicators
        if dataset.summary:
            summary_lower = dataset.summary.lower()
            if 'dna methylation' in summary_lower or 'methylome' in summary_lower:
                # Only skip if it's primarily about methylation, not just mentions it
                if 'gene expression' not in summary_lower and 'transcriptome' not in summary_lower:
                    logger.debug(f"{dataset.accession}: Skipping - summary indicates primarily methylation study")
                    return True
        
        return False
    
    def _has_survival_indicators_in_metadata(self, dataset: GEODataset) -> bool:
        """
        Check if dataset description suggests actual survival metadata is available.
        Datasets that mention survival in context of actual patient follow-up are preferred.
        
        Returns:
            True if dataset likely has survival data in sample metadata
        """
        text = f"{dataset.title} {dataset.summary}".lower()
        
        # Strong indicators that survival data is actually IN the dataset
        strong_survival_indicators = [
            'overall survival',
            'survival time',
            'survival data',
            'survival status',
            'survival information',
            'follow-up data',
            'follow up data',
            'clinical outcome data',
            'patient outcome data',
            'time to death',
            'time to event',
            'days to death',
            'months to death',
            'survival months',
            'survival days',
            'os (month',
            'os (day',
            'pfs (month',
            'dfs (month',
            'rfs (month',
            'survival curve',
            'kaplan-meier',
            'kaplan meier',
            'cox regression',
            'hazard ratio',
            'censored',
            'censoring',
            # Mouse/aging specific
            'lifespan data',
            'lifespan measurement',
            'age at death',
            'survival data from',
        ]
        
        for indicator in strong_survival_indicators:
            if indicator in text:
                return True
        
        return False
    
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

            YOUR TWO MAIN CRITERIA FOR SCORING (BOTH MATTER EQUALLY):
            
            1. RELEVANCE TO USER'S QUERY (does the dataset match what the user is asking about?)
               - The dataset topic should align with the user's question
               - For cancer queries: dataset should study that specific cancer type
               - For caloric restriction: dataset should study CR, aging, or longevity
               
            2. AVAILABILITY OF SURVIVAL DATA (can we actually do survival analysis?)
               - A TIME column (survival time, follow-up time, days to death, lifespan)
               - An EVENT column (death/alive status, event indicator, censoring status)

            SCORING BASED ON BOTH CRITERIA:

            HIGH SCORE (8-10) - RELEVANT + HAS SURVIVAL DATA:
            - Dataset topic matches query AND has survival endpoint data
            - Cancer queries: specific cancer type + "overall survival", "Kaplan-Meier", "prognosis"
            - Aging queries: CR/aging study + "lifespan data", "survival curves", "age at death"
            - Sample size n >= 30 with survival follow-up

            MEDIUM SCORE (5-7) - PARTIALLY MATCHES:
            - Topic matches but survival data uncertain
            - OR survival data present but topic only partially matches
            - Cancer cohorts mentioning "clinical outcome" or "prognostic"

            LOW SCORE (0-4) - POOR MATCH:
            - Topic doesn't match user query
            - Cell line studies (score 0-1) - cells don't have survival
            - Single timepoint tissue samples without follow-up
            - Studies without survival/outcome endpoints

            IMPORTANT FOR QUERY MATCHING:
            - "breast cancer" query → prioritize breast cancer datasets over other cancers
            - "lung cancer" query → prioritize lung cancer datasets
            - "colorectal cancer" query → prioritize colorectal/colon cancer datasets
            - "caloric restriction lifespan" → prioritize aging/CR datasets in mice

            A dataset about the WRONG cancer type should score lower even if it has survival data."""
    
    async def rank_datasets(
        self,
        datasets: List[GEODataset],
        query: str,
        top_k: int = 20
    ) -> RankingResult:
        """
        Rank datasets by survival analysis potential and platform size.
        Smaller platforms and single platforms are preferred.

        Args:
            datasets: Datasets to rank
            query: Original search query
            top_k: Number of top datasets to return
            min_survival_score: Minimum survival score to include (default 5.0)

        Returns:
            RankingResult with ranked datasets, quality score, and recommendations
        """
        if not datasets:
            logger.warning("No datasets to rank")
            return RankingResult(datasets=[], quality_score=0.0, recommendations="No datasets available to rank.")
        
        logger.info(f"Ranking {len(datasets)} datasets for survival analysis potential, query: {query}")
        
        # STEP 1: Early filtering - remove methylation/non-expression datasets
        expression_datasets = []
        skipped_methylation = []
        for ds in datasets:
            if self._is_methylation_or_non_expression(ds):
                skipped_methylation.append(ds.accession)
            else:
                expression_datasets.append(ds)
        
        if skipped_methylation:
            logger.info(f"  Filtered out {len(skipped_methylation)} methylation/non-expression datasets: {skipped_methylation[:5]}{'...' if len(skipped_methylation) > 5 else ''}")
        
        if not expression_datasets:
            logger.warning("All datasets were filtered out as methylation/non-expression")
            return RankingResult(
                datasets=[],
                quality_score=0.0,
                recommendations="All datasets were methylation or non-expression arrays. Try a more specific search."
            )
        
        # STEP 2: Prioritize datasets with strong survival indicators
        datasets_with_survival_hints = []
        datasets_without_hints = []
        for ds in expression_datasets:
            if self._has_survival_indicators_in_metadata(ds):
                datasets_with_survival_hints.append(ds)
            else:
                datasets_without_hints.append(ds)
        
        logger.info(f"  Found {len(datasets_with_survival_hints)} datasets with survival indicators in description")
        
        # Put datasets with survival hints first, then others
        prioritized_datasets = datasets_with_survival_hints + datasets_without_hints
        
        max_datasets_for_llm = min(len(prioritized_datasets), 25)
        dataset_summaries = await self._prepare_dataset_summaries(prioritized_datasets[:max_datasets_for_llm])
        
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
            
            # Use prioritized_datasets (filtered, without methylation)
            reordered = await self._reorder_datasets(prioritized_datasets, ranked.datasets)
            
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
                return RankingResult(
                    datasets=reordered[:top_k],
                    quality_score=ranked.overall_quality,
                    recommendations=ranked.recommendations
                )

            logger.info(f"  {len(filtered)} datasets passed survival score threshold ({min_survival_score})")
            return RankingResult(
                datasets=filtered[:top_k],
                quality_score=ranked.overall_quality,
                recommendations=ranked.recommendations
            )

        except Exception as e:
            logger.error(f"Dataset ranking failed: {e}")
            return RankingResult(
                datasets=prioritized_datasets[:top_k],
                quality_score=0.0,
                recommendations=f"Ranking failed: {str(e)}"
            )
    
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
        """Build prompt for dataset ranking focused on query relevance AND survival analysis potential"""
        
        prompt = f"""User Query: "{query}"

Datasets to evaluate and rank:

{json.dumps(dataset_summaries, indent=2)}

SCORING INSTRUCTIONS - CONSIDER BOTH QUERY RELEVANCE AND SURVIVAL DATA:

You must evaluate datasets based on TWO criteria:
1. Does the dataset MATCH THE USER'S QUERY? (topic relevance)
2. Does the dataset HAVE SURVIVAL DATA? (data availability)

SCORE 8-10 (HIGH - RELEVANT + HAS SURVIVAL DATA):
- Dataset topic directly matches user's query
- AND explicitly mentions survival endpoint data:
  - "survival analysis", "overall survival", "OS", "PFS", "RFS", "DFS"
  - "Kaplan-Meier", "Cox regression", "hazard ratio"
  - "prognosis" AND "outcome" with time component
  - For mice: "lifespan data", "survival curves", "age at death"
- Sample size n >= 30

SCORE 5-7 (MEDIUM - PARTIAL MATCH):
- Topic matches query but survival data uncertain
- OR topic is related but not exact match
- Cancer cohort mentioning "clinical outcome" or "prognostic"

SCORE 0-4 (LOW - POOR MATCH OR NO SURVIVAL DATA):
- Topic doesn't match user's query (e.g., wrong cancer type)
- Cell lines (score 0-1) - cells don't have survival
- No mention of survival/prognosis/outcome
- Pure mechanistic studies without clinical endpoints

QUERY RELEVANCE IS CRITICAL:
- If user asks about "breast cancer" → breast cancer datasets score higher
- If user asks about "lung cancer" → lung cancer datasets score higher  
- If user asks about "caloric restriction" → CR/aging datasets score higher
- A breast cancer dataset should score LOW for a lung cancer query even if it has survival data

For each dataset provide:
1. accession: The GEO accession
2. survival_score: Score 0-10 (considering BOTH query match AND survival data)
3. rationale: Why this score - mention both relevance to query AND survival data availability

Also provide:
- overall_quality: Quality of this collection for the user's query (0-10)
- recommendations: How to improve results for this specific query"""
        
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