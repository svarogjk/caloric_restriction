"""
Query validation utilities for checking SQL before execution.
"""
import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class QueryValidator:
    """Validate SQL queries before execution."""

    def __init__(self, session: AsyncSession):
        """
        Initialize query validator.

        Args:
            session: Database session for validation
        """
        self.session = session

    async def validate_syntax(self, query: str) -> dict[str, Any]:
        """
        Validate SQL query syntax without executing it.

        Args:
            query: SQL query to validate

        Returns:
            Validation result with status and error if any
        """
        try:
            # Use EXPLAIN to validate syntax
            await self.session.execute(text(f"EXPLAIN {query}"))
            return {"valid": True, "error": None}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def get_execution_plan(self, query: str) -> dict[str, Any]:
        """
        Get query execution plan for performance analysis.

        Args:
            query: SQL query to analyze

        Returns:
            Execution plan details
        """
        try:
            result = await self.session.execute(
                text(f"EXPLAIN (FORMAT JSON, VERBOSE, BUFFERS) {query}")
            )
            plan_json = result.scalar()

            if isinstance(plan_json, str):
                plan = json.loads(plan_json)
            else:
                plan = plan_json

            return {"success": True, "plan": plan, "error": None}
        except Exception as e:
            logger.error(f"Failed to get execution plan: {e}")
            return {"success": False, "plan": None, "error": str(e)}

    async def analyze_performance(self, query: str) -> dict[str, Any]:
        """
        Analyze query performance and provide recommendations.

        Args:
            query: SQL query to analyze

        Returns:
            Performance analysis with warnings and suggestions
        """
        plan_result = await self.get_execution_plan(query)

        if not plan_result["success"]:
            return {
                "warnings": [],
                "suggestions": [],
                "error": plan_result["error"],
            }

        plan = plan_result["plan"][0]["Plan"]

        warnings = []
        suggestions = []

        # Check for sequential scans
        if self._has_sequential_scan(plan):
            warnings.append("Sequential scan detected on potentially large table")
            suggestions.append(
                "Consider adding an index on the filtered/joined columns"
            )

        # Check for nested loops
        if self._has_nested_loop(plan):
            nested_info = self._get_nested_loop_info(plan)
            if nested_info["rows"] > 1000:
                warnings.append(
                    f"Nested loop with high row count ({nested_info['rows']})"
                )
                suggestions.append("Consider using a hash join or merge join instead")

        # Check estimated cost
        total_cost = plan.get("Total Cost", 0)
        if total_cost > 10000:
            warnings.append(f"High query cost: {total_cost:.2f}")
            suggestions.append("Review query complexity and table indexes")

        # Check for missing indexes
        if plan.get("Node Type") == "Seq Scan" and "Filter" in plan:
            relation = plan.get("Relation Name", "unknown")
            warnings.append(f"Sequential scan with filter on table '{relation}'")
            suggestions.append(f"Consider adding index on filtered columns in '{relation}'")

        return {
            "total_cost": total_cost,
            "estimated_rows": plan.get("Plan Rows", 0),
            "warnings": warnings,
            "suggestions": suggestions,
            "plan_summary": self._summarize_plan(plan),
        }

    def _has_sequential_scan(self, plan: dict[str, Any]) -> bool:
        """Check if plan contains sequential scan."""
        if plan.get("Node Type") == "Seq Scan":
            return True

        for child in plan.get("Plans", []):
            if self._has_sequential_scan(child):
                return True

        return False

    def _has_nested_loop(self, plan: dict[str, Any]) -> bool:
        """Check if plan contains nested loop."""
        if plan.get("Node Type") == "Nested Loop":
            return True

        for child in plan.get("Plans", []):
            if self._has_nested_loop(child):
                return True

        return False

    def _get_nested_loop_info(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Get nested loop information."""
        if plan.get("Node Type") == "Nested Loop":
            return {
                "rows": plan.get("Plan Rows", 0),
                "cost": plan.get("Total Cost", 0),
            }

        for child in plan.get("Plans", []):
            info = self._get_nested_loop_info(child)
            if info["rows"] > 0:
                return info

        return {"rows": 0, "cost": 0}

    def _summarize_plan(self, plan: dict[str, Any], level: int = 0) -> str:
        """Create human-readable plan summary."""
        indent = "  " * level
        node_type = plan.get("Node Type", "Unknown")
        relation = plan.get("Relation Name", "")
        rows = plan.get("Plan Rows", 0)

        summary = f"{indent}{node_type}"
        if relation:
            summary += f" on {relation}"
        summary += f" (rows={rows})\n"

        for child in plan.get("Plans", []):
            summary += self._summarize_plan(child, level + 1)

        return summary


async def validate_query(session: AsyncSession, query: str) -> dict[str, Any]:
    """
    Convenience function to validate a query.

    Args:
        session: Database session
        query: SQL query to validate

    Returns:
        Validation result with analysis
    """
    validator = QueryValidator(session)

    # Check syntax
    syntax_result = await validator.validate_syntax(query)
    if not syntax_result["valid"]:
        return {
            "valid": False,
            "error": syntax_result["error"],
            "analysis": None,
        }

    # Analyze performance
    analysis = await validator.analyze_performance(query)

    return {
        "valid": True,
        "error": None,
        "analysis": analysis,
    }
