"""
GEO Client Service
Handles search and data retrieval from NCBI Gene Expression Omnibus (GEO)
Similar architecture to ncbi_client.py
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
import httpx
import time
import re

logger = logging.getLogger(__name__)


@dataclass
class GEODataset:
    """Represents a GEO dataset"""
    
    accession: str  # GSE number
    title: str
    summary: str
    organism: str
    submission_date: str
    last_update: str
    sample_count: int
    dataset_type: str
    platform: str  # GPL number
    pmid: Optional[str] = None
    supplementary_files: List[str] = field(default_factory=list)
    ftp_link: Optional[str] = None
    series_matrix_url: Optional[str] = None


@dataclass
class GEOSearchResult:
    """Container for GEO search results"""
    
    datasets: List[GEODataset]
    total_count: int
    search_query: str
    timestamp: datetime


class GEOClient:
    """
    Client for interacting with NCBI GEO database
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    GEO_DB = "gds"
    GEO_FTP = "https://ftp.ncbi.nlm.nih.gov/geo/series"
    
    RATE_LIMIT_DELAY = 0.34
    
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key
        self.email = email
        self.last_request_time = 0
        
        if api_key:
            self.RATE_LIMIT_DELAY = 0.1
        
        self.client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": f"GEOClient/1.0 ({email if email else 'no-email'})"}
        )
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - time_since_last)
        self.last_request_time = time.time()
    
    def _build_params(self, **kwargs) -> Dict[str, str]:
        """Build parameters for NCBI API request"""
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        params.update({k: v for k, v in kwargs.items() if v is not None})
        return params
    
    def _build_geo_query(
        self,
        keywords: List[str],
        organism: Optional[str] = None,
        dataset_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> str:
        """Build GEO search query"""
        query_parts = []
        
        if keywords:
            keyword_query = " OR ".join([f'"{kw}"[All Fields]' for kw in keywords])
            query_parts.append(f"({keyword_query})")
        
        if organism:
            query_parts.append(f'"{organism}"[Organism]')
        
        if dataset_type:
            query_parts.append(f'"{dataset_type}"[DataSet Type]')
        
        if date_from and date_to:
            query_parts.append(f'("{date_from}"[Publication Date] : "{date_to}"[Publication Date])')
        
        query_parts.append('"gse"[Entry Type]')
        
        final_query = " AND ".join(query_parts)
        logger.debug(f"Built GEO query: {final_query}")
        return final_query
    
    async def search(
        self,
        keywords: List[str],
        max_results: int = 100,
        organism: Optional[str] = None,
        dataset_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> GEOSearchResult:
        """Search GEO for datasets"""
        await self._rate_limit()
        
        search_query = self._build_geo_query(
            keywords=keywords,
            organism=organism,
            dataset_type=dataset_type,
            date_from=date_from,
            date_to=date_to
        )
        
        search_params = self._build_params(
            db=self.GEO_DB,
            term=search_query,
            retmax=max_results,
            retmode="json",
            usehistory="y"
        )
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params=search_params
            )
            response.raise_for_status()
            search_data = response.json()
            
            ids = search_data.get("esearchresult", {}).get("idlist", [])
            total_count = int(search_data.get("esearchresult", {}).get("count", 0))
            
            if not ids:
                logger.info(f"No GEO datasets found for query: {search_query}")
                return GEOSearchResult(
                    datasets=[],
                    total_count=0,
                    search_query=search_query,
                    timestamp=datetime.now()
                )
            
            datasets = await self.fetch_datasets(ids)
            
            return GEOSearchResult(
                datasets=datasets,
                total_count=total_count,
                search_query=search_query,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"Error searching GEO: {e}", exc_info=True)
            logger.error(f"Search query was: {search_query}")
            raise
    
    async def fetch_datasets(self, ids: List[str]) -> List[GEODataset]:
        """Fetch detailed information for GEO dataset IDs"""
        if not ids:
            return []
        
        await self._rate_limit()
        
        batch_size = 100
        all_datasets = []
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            id_str = ",".join(batch_ids)
            
            fetch_params = self._build_params(
                db=self.GEO_DB,
                id=id_str,
                retmode="xml"
            )
            
            try:
                response = await self.client.get(
                    f"{self.BASE_URL}/esummary.fcgi",
                    params=fetch_params
                )
                response.raise_for_status()
                
                datasets = self._parse_geo_xml(response.text)
                all_datasets.extend(datasets)
                
                if i + batch_size < len(ids):
                    await self._rate_limit()
            
            except Exception as e:
                logger.error(f"Error fetching datasets batch {i//batch_size}: {e}")
                continue
        
        return all_datasets
    
    def _parse_geo_xml(self, xml_content: str) -> List[GEODataset]:
        """Parse GEO XML response"""
        datasets = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for doc_sum in root.findall(".//DocSum"):
                dataset_data = {}
                
                id_elem = doc_sum.find("Id")
                if id_elem is None:
                    continue
                
                for item in doc_sum.findall("Item"):
                    name = item.get("Name")
                    value = item.text or ""
                    dataset_data[name] = value
                
                accession = dataset_data.get("Accession", "")
                if not accession.startswith("GSE"):
                    continue
                
                dataset = GEODataset(
                    accession=accession,
                    title=dataset_data.get("title", ""),
                    summary=dataset_data.get("summary", ""),
                    organism=dataset_data.get("taxon", ""),
                    submission_date=dataset_data.get("PDAT", ""),
                    last_update=dataset_data.get("suppFile", ""),
                    sample_count=int(dataset_data.get("n_samples", 0)),
                    dataset_type=dataset_data.get("gdsType", ""),
                    platform=dataset_data.get("GPL", ""),
                    pmid=dataset_data.get("PubMedIds", None)
                )
                
                dataset.ftp_link = self._build_ftp_link(accession)
                dataset.series_matrix_url = self._build_series_matrix_url(accession)
                
                datasets.append(dataset)
        
        except Exception as e:
            logger.error(f"Error parsing GEO XML: {e}")
        
        return datasets
    
    def _build_ftp_link(self, accession: str) -> str:
        """Build FTP link for GEO series"""
        gse_num = accession[3:]
        gse_prefix = gse_num[:-3] + "nnn"
        return f"{self.GEO_FTP}/GSE{gse_prefix}/{accession}/"
    
    def _build_series_matrix_url(self, accession: str) -> str:
        """Build URL for series matrix file"""
        gse_num = accession[3:]
        gse_prefix = gse_num[:-3] + "nnn"
        return f"{self.GEO_FTP}/GSE{gse_prefix}/{accession}/matrix/{accession}_series_matrix.txt.gz"
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()