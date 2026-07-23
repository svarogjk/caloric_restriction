"""
Service for persisting and retrieving analysis results from the database.
Enables shareable URLs (F09), history dashboard (F12), and publication exports (F15).
"""
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.database import AnalysisResult

logger = logging.getLogger(__name__)


class AnalysisResultService:

    async def save_result(
        self,
        db: AsyncSession,
        result_dict: dict,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Save analysis result JSON to DB. Returns the result UUID.
        Caller should wrap in try/except — DB failure must never break the analysis response.
        """
        result_id = str(uuid.uuid4())
        record = AnalysisResult(
            id=result_id,
            user_id=user_id,
            query=result_dict.get("query", ""),
            n_datasets_analyzed=result_dict.get("n_datasets_analyzed", 0),
            n_datasets_with_survival=result_dict.get("n_datasets_with_survival", 0),
            n_genes_found=len(result_dict.get("common_genes", [])),
            processing_time_seconds=result_dict.get("processing_time"),
            result_data=result_dict,
        )
        db.add(record)
        await db.commit()
        logger.info(f"Saved analysis result {result_id} for user {user_id}")
        return result_id

    async def get_result(self, db: AsyncSession, result_id: str) -> Optional[dict]:
        """Retrieve result by ID. Returns None if not found."""
        stmt = select(AnalysisResult).where(AnalysisResult.id == result_id)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "result_id": row.id,
            "query": row.query,
            "created_at": row.created_at.isoformat(),
            **row.result_data,
        }

    async def find_recent_by_query(self, db: AsyncSession, query: str) -> Optional[dict]:
        """Find the most recent saved result whose query matches (case-insensitive).
        Used by Oncologist Mode (F20) to instantly load a pre-run curated analysis.

        Excludes zero-gene results — a query that legitimately (or transiently)
        found no significant genes would otherwise poison every future call for
        that exact query string, since callers treat any match here as a usable
        cache hit and never retry a fresh orchestrator run."""
        stmt = (
            select(AnalysisResult)
            .where(AnalysisResult.query.ilike(query), AnalysisResult.n_genes_found > 0)
            .order_by(desc(AnalysisResult.created_at))
            .limit(1)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "result_id": row.id,
            "query": row.query,
            "n_genes_found": row.n_genes_found,
            "n_datasets_with_survival": row.n_datasets_with_survival,
            "created_at": row.created_at.isoformat(),
        }

    async def list_user_results(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """List analysis results for a user, most recent first."""
        stmt = (
            select(AnalysisResult)
            .where(AnalysisResult.user_id == user_id)
            .order_by(desc(AnalysisResult.created_at))
            .limit(limit)
            .offset(offset)
        )
        rows = (await db.execute(stmt)).scalars().all()
        return [
            {
                "result_id": r.id,
                "query": r.query,
                "n_datasets_analyzed": r.n_datasets_analyzed,
                "n_datasets_with_survival": r.n_datasets_with_survival,
                "n_genes_found": r.n_genes_found,
                "processing_time_seconds": r.processing_time_seconds,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


analysis_result_service = AnalysisResultService()
