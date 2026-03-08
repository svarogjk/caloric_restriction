"""
Analysis comparison endpoint.
Compares two saved analysis results to find shared/unique genes and HR correlations.
"""
import logging
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.api.dependencies import get_current_active_user
from app.services.analysis_result_service import analysis_result_service

logger = logging.getLogger(__name__)
router = APIRouter()


class CompareRequest(BaseModel):
    result_id_a: str
    result_id_b: str


class GeneComparison(BaseModel):
    gene_symbol: str
    hr_a: float
    hr_b: float
    p_value_a: float
    p_value_b: float
    n_datasets_a: int
    n_datasets_b: int
    direction_agrees: bool   # True if both HR>1 or both HR<1


class CompareResponse(BaseModel):
    query_a: str
    query_b: str
    shared_genes: List[GeneComparison]
    unique_to_a: List[str]   # gene symbols only in A
    unique_to_b: List[str]   # gene symbols only in B
    n_shared: int
    n_unique_a: int
    n_unique_b: int
    direction_agreement_pct: Optional[float]   # % of shared genes where HR direction agrees
    spearman_r: Optional[float]               # Spearman correlation of HR values for shared genes


def _spearman_r(xs: list[float], ys: list[float]) -> Optional[float]:
    """Compute Spearman rank correlation without scipy."""
    n = len(xs)
    if n < 3:
        return None

    def rank(vals: list[float]) -> list[float]:
        sorted_vals = sorted(enumerate(vals), key=lambda x: x[1])
        ranks = [0.0] * n
        for rank_val, (orig_idx, _) in enumerate(sorted_vals, 1):
            ranks[orig_idx] = float(rank_val)
        return ranks

    rx = rank(xs)
    ry = rank(ys)

    d_sq_sum = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    r = 1 - (6 * d_sq_sum) / (n * (n * n - 1))
    return round(r, 4)


@router.post("/compare", response_model=CompareResponse)
async def compare_analyses(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Compare two saved analysis results — find shared genes and HR correlations."""
    result_a = await analysis_result_service.get_result(db, request.result_id_a)
    result_b = await analysis_result_service.get_result(db, request.result_id_b)

    if result_a is None:
        raise HTTPException(status_code=404, detail=f"Result {request.result_id_a} not found")
    if result_b is None:
        raise HTTPException(status_code=404, detail=f"Result {request.result_id_b} not found")

    # Build gene maps: symbol -> gene data
    genes_a = {
        g["gene_symbol"]: g
        for g in result_a.get("common_genes", [])
        if g.get("gene_symbol")
    }
    genes_b = {
        g["gene_symbol"]: g
        for g in result_b.get("common_genes", [])
        if g.get("gene_symbol")
    }

    shared_symbols = set(genes_a.keys()) & set(genes_b.keys())
    unique_a = sorted(set(genes_a.keys()) - shared_symbols)
    unique_b = sorted(set(genes_b.keys()) - shared_symbols)

    shared_genes = []
    for sym in sorted(shared_symbols):
        ga = genes_a[sym]
        gb = genes_b[sym]
        hr_a = ga.get("avg_hazard_ratio", 1.0)
        hr_b = gb.get("avg_hazard_ratio", 1.0)
        shared_genes.append(GeneComparison(
            gene_symbol=sym,
            hr_a=hr_a,
            hr_b=hr_b,
            p_value_a=ga.get("avg_cox_p_value", 1.0),
            p_value_b=gb.get("avg_cox_p_value", 1.0),
            n_datasets_a=ga.get("n_datasets", 0),
            n_datasets_b=gb.get("n_datasets", 0),
            direction_agrees=(hr_a > 1) == (hr_b > 1),
        ))

    direction_agreement_pct = None
    spearman_r = None
    if shared_genes:
        agrees = sum(1 for g in shared_genes if g.direction_agrees)
        direction_agreement_pct = round(agrees / len(shared_genes) * 100, 1)
        spearman_r = _spearman_r(
            [math.log(g.hr_a) for g in shared_genes],
            [math.log(g.hr_b) for g in shared_genes],
        )

    return CompareResponse(
        query_a=result_a.get("query", ""),
        query_b=result_b.get("query", ""),
        shared_genes=shared_genes,
        unique_to_a=unique_a,
        unique_to_b=unique_b,
        n_shared=len(shared_genes),
        n_unique_a=len(unique_a),
        n_unique_b=len(unique_b),
        direction_agreement_pct=direction_agreement_pct,
        spearman_r=spearman_r,
    )
