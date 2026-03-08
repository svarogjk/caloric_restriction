"""
Pathway enrichment service using g:Profiler REST API.
Free, no API key required. Supports GO, KEGG, Reactome.
"""
import logging
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)

GPROFILER_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"

ORGANISM_MAP = {
    "human": "hsapiens",
    "homo sapiens": "hsapiens",
    "hsapiens": "hsapiens",
    "mouse": "mmusculus",
    "mus musculus": "mmusculus",
    "mmusculus": "mmusculus",
    "rat": "rnorvegicus",
    "rattus norvegicus": "rnorvegicus",
}


@dataclass
class EnrichmentTerm:
    term_id: str
    term_name: str
    source: str          # GO:BP, GO:MF, GO:CC, KEGG, REAC
    p_value: float
    intersection_size: int
    query_size: int
    term_size: int
    intersection_genes: list[str] = field(default_factory=list)


class PathwayEnrichmentService:

    async def enrich(
        self,
        gene_symbols: list[str],
        organism: str = "hsapiens",
        sources: list[str] | None = None,
        fdr_threshold: float = 0.05,
    ) -> list[EnrichmentTerm]:
        """
        Run gene enrichment via g:Profiler.
        Returns terms sorted by p_value ascending, filtered by fdr_threshold.
        """
        if not gene_symbols:
            return []

        organism_id = ORGANISM_MAP.get(organism.lower(), organism)
        if sources is None:
            sources = ["GO:BP", "GO:MF", "KEGG", "REAC"]

        payload = {
            "organism": organism_id,
            "query": gene_symbols,
            "sources": sources,
            "user_threshold": fdr_threshold,
            "all_results": False,
            "ordered_query": False,
            "no_iea": False,
            "combined": False,
            "measure_underrepresentation": False,
            "domain_scope": "annotated",
            "significance_threshold_method": "fdr",
            "background": None,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GPROFILER_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        results_raw = data.get("result", [])
        terms = []
        for r in results_raw:
            terms.append(EnrichmentTerm(
                term_id=r.get("native", r.get("term_id", "")),
                term_name=r.get("name", ""),
                source=r.get("source", ""),
                p_value=r.get("p_value", 1.0),
                intersection_size=r.get("intersection_size", 0),
                query_size=r.get("query_size", len(gene_symbols)),
                term_size=r.get("term_size", 0),
                intersection_genes=r.get("intersections", []),
            ))

        terms.sort(key=lambda t: t.p_value)
        return terms[:50]


pathway_enrichment_service = PathwayEnrichmentService()
