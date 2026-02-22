"""
Schema comparison utilities for detecting differences between models and database.
"""
import logging
from typing import Any

from sqlalchemy import MetaData, create_engine, inspect

from app.config.settings import settings
from app.models.database import Base

logger = logging.getLogger(__name__)


class SchemaDiff:
    """Compare SQLAlchemy models with actual database schema."""

    def __init__(self):
        """Initialize schema diff analyzer."""
        # Use sync engine for inspection
        sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
        self.engine = create_engine(sync_url)
        self.inspector = inspect(self.engine)
        self.metadata = Base.metadata

    def get_table_diff(self) -> dict[str, Any]:
        """
        Compare tables between models and database.

        Returns:
            Dictionary with table differences
        """
        db_tables = set(self.inspector.get_table_names())
        model_tables = set(self.metadata.tables.keys())

        return {
            "new_tables": list(model_tables - db_tables),
            "removed_tables": list(db_tables - model_tables),
            "common_tables": list(model_tables & db_tables),
        }

    def get_column_diff(self, table_name: str) -> dict[str, Any]:
        """
        Compare columns for a specific table.

        Args:
            table_name: Name of table to compare

        Returns:
            Dictionary with column differences
        """
        if table_name not in self.metadata.tables:
            return {"error": f"Table {table_name} not in models"}

        model_table = self.metadata.tables[table_name]
        db_columns = {col["name"]: col for col in self.inspector.get_columns(table_name)}
        model_columns = {col.name: col for col in model_table.columns}

        new_cols = set(model_columns.keys()) - set(db_columns.keys())
        removed_cols = set(db_columns.keys()) - set(model_columns.keys())
        common_cols = set(model_columns.keys()) & set(db_columns.keys())

        # Check type changes for common columns
        type_changes = []
        for col_name in common_cols:
            model_col = model_columns[col_name]
            db_col = db_columns[col_name]

            model_type = str(model_col.type)
            db_type = str(db_col["type"])

            if model_type.lower() != db_type.lower():
                type_changes.append(
                    {
                        "column": col_name,
                        "model_type": model_type,
                        "db_type": db_type,
                    }
                )

        return {
            "new_columns": list(new_cols),
            "removed_columns": list(removed_cols),
            "type_changes": type_changes,
        }

    def get_index_diff(self, table_name: str) -> dict[str, Any]:
        """
        Compare indexes for a specific table.

        Args:
            table_name: Name of table to compare

        Returns:
            Dictionary with index differences
        """
        if table_name not in self.metadata.tables:
            return {"error": f"Table {table_name} not in models"}

        model_table = self.metadata.tables[table_name]
        db_indexes = {idx["name"] for idx in self.inspector.get_indexes(table_name)}
        model_indexes = {idx.name for idx in model_table.indexes if idx.name}

        return {
            "new_indexes": list(model_indexes - db_indexes),
            "removed_indexes": list(db_indexes - model_indexes),
        }

    def get_full_diff(self) -> dict[str, Any]:
        """
        Get complete schema diff report.

        Returns:
            Comprehensive diff report
        """
        table_diff = self.get_table_diff()

        column_diffs = {}
        index_diffs = {}

        for table_name in table_diff["common_tables"]:
            col_diff = self.get_column_diff(table_name)
            idx_diff = self.get_index_diff(table_name)

            if (
                col_diff["new_columns"]
                or col_diff["removed_columns"]
                or col_diff["type_changes"]
            ):
                column_diffs[table_name] = col_diff

            if idx_diff["new_indexes"] or idx_diff["removed_indexes"]:
                index_diffs[table_name] = idx_diff

        has_changes = bool(
            table_diff["new_tables"]
            or table_diff["removed_tables"]
            or column_diffs
            or index_diffs
        )

        return {
            "has_changes": has_changes,
            "tables": table_diff,
            "columns": column_diffs,
            "indexes": index_diffs,
        }

    def print_report(self) -> None:
        """Print human-readable schema diff report."""
        diff = self.get_full_diff()

        print("=== SCHEMA DIFF ANALYSIS ===\n")

        if not diff["has_changes"]:
            print("✓ Schema is in sync - no changes detected")
            return

        # Tables
        if diff["tables"]["new_tables"]:
            print("🆕 Tables to CREATE:")
            for table in diff["tables"]["new_tables"]:
                print(f"  - {table}")
            print()

        if diff["tables"]["removed_tables"]:
            print("🗑️  Tables to DROP:")
            for table in diff["tables"]["removed_tables"]:
                print(f"  - {table}")
            print()

        # Columns
        if diff["columns"]:
            print("📋 Column changes:")
            for table_name, col_diff in diff["columns"].items():
                print(f"\n  Table: {table_name}")
                if col_diff["new_columns"]:
                    print(f"    + Add columns: {', '.join(col_diff['new_columns'])}")
                if col_diff["removed_columns"]:
                    print(
                        f"    - Remove columns: {', '.join(col_diff['removed_columns'])}"
                    )
                if col_diff["type_changes"]:
                    print("    ~ Type changes:")
                    for change in col_diff["type_changes"]:
                        print(
                            f"      {change['column']}: {change['db_type']} -> {change['model_type']}"
                        )
            print()

        # Indexes
        if diff["indexes"]:
            print("🔍 Index changes:")
            for table_name, idx_diff in diff["indexes"].items():
                print(f"\n  Table: {table_name}")
                if idx_diff["new_indexes"]:
                    print(f"    + Create: {', '.join(idx_diff['new_indexes'])}")
                if idx_diff["removed_indexes"]:
                    print(f"    - Drop: {', '.join(idx_diff['removed_indexes'])}")
            print()


def check_schema_sync() -> bool:
    """
    Quick check if schema is in sync.

    Returns:
        True if schema matches models, False otherwise
    """
    try:
        diff = SchemaDiff()
        result = diff.get_full_diff()
        return not result["has_changes"]
    except Exception as e:
        logger.error(f"Schema check failed: {e}")
        return False
