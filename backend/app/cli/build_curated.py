"""CLI to (re)build the curated Oncologist-Mode prognostic models.

Startup builds these automatically (real when cohorts are cached, else demo).
Use this to force a real rebuild once GEO cohorts are cached locally:

    uv run python -m app.cli.build_curated            # upgrade demos -> real where possible
    uv run python -m app.cli.build_curated --force    # rebuild all from real data
"""

import asyncio

import click

from app.config.database import get_db_session
from app.config.settings import settings
from app.services.curated_models import ensure_curated_models
from app.services.geo_survival_workflow_orchestrator import GEOSurvivalWorkflowOrchestrator
from app.services.signature_service import SignatureService


async def _run(force: bool) -> None:
    orchestrator = GEOSurvivalWorkflowOrchestrator(
        api_key=settings.ncbi_api_key or None, email=settings.email, model="mistral"
    )
    svc = SignatureService(orchestrator=orchestrator)
    svc.load_persisted_models()
    try:
        async with get_db_session() as db:
            built = await ensure_curated_models(svc, db, prefer_real=True, force=force)
    finally:
        await orchestrator.close()

    for key, model_id in built.items():
        model = svc.find_model_by_cancer(key)
        kind = "demo" if (model and model.is_demo) else "real"
        c_index = f"{model.pooled_c_index:.3f}" if model else "?"
        click.echo(f"  {key:12s} {model_id:18s} [{kind}]  C-index={c_index}")


@click.command()
@click.option("--force", is_flag=True, help="Rebuild every model from real data, replacing existing ones.")
def build_curated(force: bool) -> None:
    """(Re)build curated prognostic models from cached analysis results."""
    click.echo("Building curated prognostic models…")
    asyncio.run(_run(force))
    click.echo("Done.")


if __name__ == "__main__":
    build_curated()
