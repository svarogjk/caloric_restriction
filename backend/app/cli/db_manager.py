"""
Database management CLI tool for schema diff, query validation, and N+1 detection.
"""
import asyncio
import sys
from typing import Optional

import click

from app.config.database import get_db
from app.utils.query_monitor import QueryMonitor, enable_query_monitoring
from app.utils.query_validator import validate_query
from app.utils.schema_diff import SchemaDiff


@click.group()
def cli():
    """Database management utilities."""
    pass


@cli.command()
def schema_diff():
    """Check for differences between models and database schema."""
    try:
        diff = SchemaDiff()
        diff.print_report()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
async def validate(query: str):
    """Validate SQL query syntax and analyze performance."""
    session_gen = get_db()
    session = await anext(session_gen)

    try:
        result = await validate_query(session, query)

        if not result["valid"]:
            click.echo(f"❌ Invalid query: {result['error']}", err=True)
            sys.exit(1)

        click.echo("✅ Query is valid\n")

        analysis = result["analysis"]
        click.echo(f"Estimated cost: {analysis['total_cost']:.2f}")
        click.echo(f"Estimated rows: {analysis['estimated_rows']}\n")

        if analysis["warnings"]:
            click.echo("⚠️  Warnings:")
            for warning in analysis["warnings"]:
                click.echo(f"  - {warning}")
            click.echo()

        if analysis["suggestions"]:
            click.echo("💡 Suggestions:")
            for suggestion in analysis["suggestions"]:
                click.echo(f"  - {suggestion}")
            click.echo()

        click.echo("Execution plan:")
        click.echo(analysis["plan_summary"])

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--threshold", default=5, help="Alert threshold for repeated queries")
async def monitor(threshold: int):
    """Monitor queries for N+1 patterns (requires running application)."""
    monitor = QueryMonitor(alert_threshold=threshold)
    enable_query_monitoring()

    click.echo(f"🔍 Query monitoring enabled (threshold: {threshold})")
    click.echo("Run your application and watch for N+1 alerts...")
    click.echo("Press Ctrl+C to stop and see report\n")

    try:
        # Keep running until interrupted
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        click.echo("\n\n=== QUERY MONITORING REPORT ===\n")
        report = monitor.get_report()

        click.echo(f"Total queries: {report['total_queries']}")
        click.echo(f"Unique patterns: {report['unique_patterns']}")
        click.echo(f"Efficiency ratio: {report['efficiency_ratio']:.2f}")

        if report["has_potential_n_plus_1"]:
            click.echo("\n⚠️  POTENTIAL N+1 DETECTED\n")

        if report["top_repeated_queries"]:
            click.echo("\nTop repeated queries:")
            for i, query_info in enumerate(report["top_repeated_queries"], 1):
                click.echo(
                    f"{i}. Count: {query_info['count']} | {query_info['pattern']}"
                )


@cli.command()
@click.option("--migration-message", "-m", help="Migration description")
def auto_migrate(migration_message: Optional[str]):
    """Detect model changes and generate migration."""
    try:
        diff = SchemaDiff()
        full_diff = diff.get_full_diff()

        if not full_diff["has_changes"]:
            click.echo("✓ No schema changes detected")
            return

        click.echo("Schema changes detected:\n")
        diff.print_report()

        if not migration_message:
            migration_message = click.prompt(
                "\nEnter migration message", default="auto_generated_migration"
            )

        click.echo(f"\nGenerating migration: {migration_message}")

        # Run alembic autogenerate
        import subprocess

        result = subprocess.run(
            ["uv", "run", "alembic", "revision", "--autogenerate", "-m", migration_message],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            click.echo("✅ Migration generated successfully")
            click.echo("\n⚠️  IMPORTANT: Review the generated migration file before applying!")
            click.echo("Apply with: cd backend && uv run alembic upgrade head")
        else:
            click.echo(f"❌ Failed to generate migration:\n{result.stderr}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("sql_file", type=click.Path(exists=True))
async def validate_file(sql_file: str):
    """Validate all queries in a SQL file."""
    with open(sql_file) as f:
        queries = f.read().split(";")

    session_gen = get_db()
    session = await anext(session_gen)

    try:
        for i, query in enumerate(queries, 1):
            query = query.strip()
            if not query:
                continue

            click.echo(f"\n=== Query {i} ===")
            result = await validate_query(session, query)

            if not result["valid"]:
                click.echo(f"❌ Invalid: {result['error']}", err=True)
            else:
                click.echo("✅ Valid")
                if result["analysis"]["warnings"]:
                    click.echo(f"  Warnings: {len(result['analysis']['warnings'])}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    # Handle async commands
    for cmd in [validate, monitor, validate_file]:
        if cmd in sys.argv:
            asyncio.run(cli.main(standalone_mode=False))
            return

    cli()


if __name__ == "__main__":
    main()
