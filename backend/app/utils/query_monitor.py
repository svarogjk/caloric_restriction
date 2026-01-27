"""
Query monitoring utilities for detecting N+1 queries and performance issues.
"""
import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class QueryMonitor:
    """Monitor SQLAlchemy queries to detect N+1 patterns and performance issues."""

    def __init__(self, alert_threshold: int = 5):
        """
        Initialize query monitor.

        Args:
            alert_threshold: Number of similar queries before alerting
        """
        self.queries: list[str] = []
        self.query_counts: defaultdict[str, int] = defaultdict(int)
        self.alert_threshold = alert_threshold
        self.enabled = False

    def track_query(
        self,
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Track executed query and detect patterns."""
        if not self.enabled:
            return

        # Normalize query (remove WHERE clauses to group similar queries)
        normalized = statement.split("WHERE")[0] if "WHERE" in statement else statement
        normalized = normalized.strip()

        self.query_counts[normalized] += 1
        self.queries.append(statement)

        # Alert on potential N+1
        if self.query_counts[normalized] == self.alert_threshold:
            logger.warning(
                "POTENTIAL N+1 DETECTED: Same query pattern executed %d times",
                self.query_counts[normalized],
            )
            logger.warning("Query pattern: %s", normalized[:200])

    def reset(self) -> None:
        """Reset monitoring state."""
        self.queries.clear()
        self.query_counts.clear()

    def enable(self) -> None:
        """Enable query monitoring."""
        self.enabled = True
        logger.info("Query monitoring enabled")

    def disable(self) -> None:
        """Disable query monitoring."""
        self.enabled = False
        logger.info("Query monitoring disabled")

    def get_report(self) -> dict[str, Any]:
        """
        Generate report of query patterns.

        Returns:
            Dictionary with query statistics
        """
        total_queries = len(self.queries)
        unique_patterns = len(self.query_counts)

        # Find top repeated queries
        top_repeated = sorted(
            self.query_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Detect potential N+1
        has_n_plus_1 = any(count >= self.alert_threshold for count in self.query_counts.values())

        return {
            "total_queries": total_queries,
            "unique_patterns": unique_patterns,
            "has_potential_n_plus_1": has_n_plus_1,
            "top_repeated_queries": [
                {"pattern": pattern[:100], "count": count}
                for pattern, count in top_repeated
            ],
            "efficiency_ratio": unique_patterns / total_queries if total_queries > 0 else 1.0,
        }


# Global monitor instance
monitor = QueryMonitor()


def enable_query_monitoring() -> None:
    """Enable global query monitoring."""
    monitor.enable()
    event.listen(Engine, "before_cursor_execute", monitor.track_query)


def disable_query_monitoring() -> None:
    """Disable global query monitoring."""
    monitor.disable()
    event.remove(Engine, "before_cursor_execute", monitor.track_query)


def get_query_report() -> dict[str, Any]:
    """Get current query monitoring report."""
    return monitor.get_report()
