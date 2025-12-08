"""
AI-powered Gene Mapping Agent
Uses Claude or Mistral to understand GPL file structure and extract gene mappings efficiently
Reads only necessary tokens to understand file format, avoiding processing millions of lines
"""

import logging
import gzip
import asyncio
from typing import Dict, Optional, Literal
from pydantic_ai import Agent
from pydantic import BaseModel

from app.models.llm_models import mistral_model, anthropic_model

logger = logging.getLogger(__name__)


class FileStructureAnalysis(BaseModel):
    """Analysis of GPL file structure"""
    header_line: str
    id_column_index: int
    id_column_name: str
    gene_symbol_column_index: int
    gene_symbol_column_name: str
    confidence: float
    reasoning: str


class GeneMappingResult(BaseModel):
    """Result of AI-guided gene mapping"""
    mappings: Dict[str, str]
    total_lines_processed: int
    mapping_count: int
    success: bool


class GeneMappingAIAgent:
    """
    AI agent for intelligent gene mapping from GPL platform files.
    Uses AI to understand file structure with minimal token usage.
    """
    
    # Sample size for structure analysis (read first N lines)
    SAMPLE_SIZE = 2000
    BATCH_SIZE = 1000
    MAX_MAPPING_SAMPLES = 10000
    
    def __init__(self, model_type: Literal["claude", "mistral"] = "claude"):
        """
        Initialize the gene mapping AI agent.
        
        Args:
            model_type: Which model to use - "claude" or "mistral"
        """
        self.model_type = model_type
        self.selected_model = anthropic_model if model_type == "claude" else mistral_model
        
        # Create the structure analysis agent
        self.structure_agent = Agent(
            model=self.selected_model,
            system_prompt="""You are an expert bioinformatics data analyst specializing in GEO platform file formats.
Your task is to analyze GPL (GEO Platform) file samples and determine:
1. Which column contains probe IDs
2. Which column contains gene symbols
3. The exact header line format

Respond with JSON containing:
- header_line: The exact header line from the file
- id_column_index: Zero-based index of the ID column
- id_column_name: Name of the ID column
- gene_symbol_column_index: Zero-based index of the gene symbol column
- gene_symbol_column_name: Name of the gene symbol column
- confidence: Your confidence (0-1) that this analysis is correct
- reasoning: Your reasoning for these choices

Be precise and conservative in your analysis."""
        )
        
        # Create the mapping parsing agent
        self.parsing_agent = Agent(
            model=self.selected_model,
            system_prompt="""You are an expert at parsing bioinformatics data.
Given the column structure and a sample of data rows, extract all valid probe ID to gene symbol mappings.
Skip rows with missing or invalid gene symbols (null, na, empty).
For multiple genes per probe (separated by ///), use only the first one.

Return a JSON object with probe_id -> gene_symbol mappings."""
        )
        
        logger.info(f"Gene mapping AI agent initialized with model: {model_type}")
    
    async def analyze_file_structure(
        self,
        content_sample: str,
        platform_id: str
    ) -> FileStructureAnalysis:
        """
        Use AI to analyze GPL file structure from a small sample.
        
        Args:
            content_sample: First N lines of the GPL file
            platform_id: Platform ID for logging
        
        Returns:
            FileStructureAnalysis with column information
        """
        logger.info(f"Analyzing file structure for {platform_id} with AI ({self.model_type})")
        
        try:
            result = await self.structure_agent.run(
                f"""Analyze this GPL file sample and identify the structure:

{content_sample}

Identify the probe ID column and gene symbol column. Be precise about column indices."""
            )
            
            # Parse the AI response
            import json
            import re
            
            # Extract JSON from the response (result.output contains the text response)
            response_text = result.output if hasattr(result, 'output') else str(result)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                analysis_data = json.loads(json_match.group())
                analysis = FileStructureAnalysis(**analysis_data)
                logger.info(f"Structure analysis complete for {platform_id}: "
                           f"ID col={analysis.id_column_index}, Gene col={analysis.gene_symbol_column_index}, "
                           f"confidence={analysis.confidence}")
                return analysis
            else:
                raise ValueError("Could not parse AI response as JSON")
                
        except Exception as e:
            logger.error(f"Error analyzing file structure for {platform_id}: {e}")
            raise
    
    async def extract_mappings_from_sample(
        self,
        data_lines: list,
        header_line: str,
        id_col_idx: int,
        gene_col_idx: int,
        platform_id: str
    ) -> Dict[str, str]:
        """
        Extract mappings from data lines using the identified columns.
        This is fast and doesn't need AI for actual parsing.
        
        Args:
            data_lines: List of data lines from the file
            header_line: The header line (for logging/verification)
            id_col_idx: Column index for probe IDs
            gene_col_idx: Column index for gene symbols
            platform_id: Platform ID for logging
        
        Returns:
            Dictionary of probe_id -> gene_symbol mappings
        """
        logger.info(f"Extracting mappings from {len(data_lines)} lines for {platform_id}")
        
        mappings = {}
        invalid_count = 0
        
        for line_idx, line in enumerate(data_lines):
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            
            # Validate column indices
            if len(parts) <= max(id_col_idx, gene_col_idx):
                invalid_count += 1
                continue
            
            try:
                probe_id = parts[id_col_idx].strip()
                gene_symbol = parts[gene_col_idx].strip()
                
                # Skip empty or invalid entries
                if not probe_id or not gene_symbol:
                    invalid_count += 1
                    continue
                
                # Handle multiple genes (separated by ///)
                if '///' in gene_symbol:
                    gene_symbol = gene_symbol.split('///')[0].strip()
                
                # Skip null/na entries
                if gene_symbol.lower() in ['null', 'na', '']:
                    invalid_count += 1
                    continue
                
                mappings[probe_id] = gene_symbol
                
            except (IndexError, AttributeError):
                invalid_count += 1
                continue
        
        logger.info(f"Extracted {len(mappings)} valid mappings from {len(data_lines)} lines "
                   f"({invalid_count} invalid)")
        return mappings
    
    async def process_gpl_file(
        self,
        gpl_content: str,
        platform_id: str,
        use_ai_analysis: bool = True
    ) -> GeneMappingResult:
        """
        Process a GPL file to extract gene mappings.
        
        Args:
            gpl_content: The full or partial GPL file content
            platform_id: Platform ID for logging
            use_ai_analysis: Whether to use AI for structure analysis
        
        Returns:
            GeneMappingResult with mappings and metadata
        """
        logger.info(f"Processing GPL file for {platform_id} (size: {len(gpl_content)} chars)")
        
        lines = gpl_content.split('\n')
        header_line = None
        id_col_idx = None
        gene_col_idx = None
        
        try:
            if use_ai_analysis:
                # Take sample for AI analysis
                sample_lines = lines[:self.SAMPLE_SIZE]
                sample_content = '\n'.join(sample_lines)
                
                # Use AI to understand structure
                analysis = await self.analyze_file_structure(sample_content, platform_id)
                
                id_col_idx = analysis.id_column_index
                gene_col_idx = analysis.gene_symbol_column_index
                header_line = analysis.header_line
                
                logger.info(f"AI analysis results: ID col={id_col_idx}, Gene col={gene_col_idx}, "
                           f"confidence={analysis.confidence}")
            else:
                # Fall back to heuristic-based detection
                for idx, line in enumerate(lines[:self.SAMPLE_SIZE]):
                    if line.startswith('#ID') or 'ID_REF' in line:
                        header_line = line
                        headers = line.split('\t')
                        
                        for col_idx, header in enumerate(headers):
                            header_clean = header.lstrip('#').upper()
                            
                            if header_clean in ['ID', 'ID_REF', 'PROBE_ID']:
                                id_col_idx = col_idx
                            elif any(x in header_clean for x in ['GENE_SYMBOL', 'SYMBOL', 'GENE']):
                                gene_col_idx = col_idx
                        
                        break
            
            # Validate we found columns
            if id_col_idx is None or gene_col_idx is None:
                logger.error(f"Could not identify probe ID or gene symbol columns for {platform_id}")
                return GeneMappingResult(
                    mappings={},
                    total_lines_processed=0,
                    mapping_count=0,
                    success=False
                )
            
            # Extract mappings from sample of data lines
            # Process in batches to avoid memory issues
            data_start = next((i for i, line in enumerate(lines) if line and not line.startswith('#')), 0)
            data_lines = lines[data_start:data_start + self.MAX_MAPPING_SAMPLES]
            
            mappings = await self.extract_mappings_from_sample(
                data_lines,
                header_line or "",
                id_col_idx,
                gene_col_idx,
                platform_id
            )
            
            return GeneMappingResult(
                mappings=mappings,
                total_lines_processed=len(data_lines),
                mapping_count=len(mappings),
                success=len(mappings) > 0
            )
        
        except Exception as e:
            logger.error(f"Error processing GPL file for {platform_id}: {e}")
            return GeneMappingResult(
                mappings={},
                total_lines_processed=0,
                mapping_count=0,
                success=False
            )
    
    async def process_gpl_file_from_url(
        self,
        url: str,
        platform_id: str,
        timeout_seconds: float = 120.0
    ) -> GeneMappingResult:
        """
        Download and process a GPL file from URL.
        
        Args:
            url: URL to the GPL file (gzipped)
            platform_id: Platform ID for logging
            timeout_seconds: Timeout for download
        
        Returns:
            GeneMappingResult with mappings
        """
        logger.info(f"Downloading GPL file for {platform_id} from: {url}")
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.error(f"Failed to download {platform_id}: HTTP {response.status_code}")
                    return GeneMappingResult(
                        mappings={},
                        total_lines_processed=0,
                        mapping_count=0,
                        success=False
                    )
                
                # Decompress
                logger.debug(f"Decompressing {platform_id} ({len(response.content)} bytes)")
                content = gzip.decompress(response.content).decode('utf-8', errors='ignore')
                
                # Process
                return await self.process_gpl_file(content, platform_id, use_ai_analysis=True)
        
        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading {platform_id}")
            return GeneMappingResult(
                mappings={},
                total_lines_processed=0,
                mapping_count=0,
                success=False
            )
        except Exception as e:
            logger.error(f"Error downloading/processing {platform_id}: {e}")
            return GeneMappingResult(
                mappings={},
                total_lines_processed=0,
                mapping_count=0,
                success=False
            )
